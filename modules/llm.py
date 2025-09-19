"""LLM interaction module"""
import asyncio
import aiohttp
import re
from datetime import datetime
from config.settings import (
    LLM_PROVIDER, OPENROUTER_API_KEY, OPENROUTER_URL,
    OPENROUTER_FALLBACK_MODEL,
    OLLAMA_URL, OLLAMA_KEEP_ALIVE, OLLAMA_NUM_PREDICT,
    OLLAMA_TEMPERATURE, OLLAMA_TOP_K, OLLAMA_TOP_P, OLLAMA_REPEAT_PENALTY,
    LLM_TIMEOUT, MAX_RETRIES, BASE_RETRY_DELAY, MAX_CONTEXT_LOOKBACK,
    FILTERED_WORDS, ENABLE_PRICE_TRACKING
)
from config.personality import BOT_PERSONALITY
from utils.helpers import filter_bot_triggers, get_display_name, detect_code_in_message
from utils.formatting import summarize_search_results
from modules.context import room_message_history, conversation_context, create_comprehensive_summary
from modules.web_search import needs_web_search, search_with_jina, search_technical_docs
from modules.price_tracker import price_tracker

# Import settings_manager to get runtime settings
from modules.settings_manager import settings_manager

async def get_llm_reply_with_retry(prompt, context=None, previous_message=None, room_id=None, url_contents=None):
    """Wrapper with retry logic and exponential backoff"""
    for attempt in range(MAX_RETRIES):
        try:
            return await get_llm_reply(prompt, context, previous_message, room_id, url_contents)
        except asyncio.TimeoutError:
            if attempt == MAX_RETRIES - 1:
                print(f"[ERROR] All retry attempts failed due to timeout")
                return "Damn, the AI servers are timing out hard rn. Maybe try again in a minute? 💀"
            
            delay = BASE_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
            print(f"[RETRY] Attempt {attempt + 1} timed out, retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"[ERROR] All retry attempts failed: {e}")
                return "Yo, the AI servers are really struggling rn. Maybe try again in a minute? 🔧"
            
            delay = BASE_RETRY_DELAY * (2 ** attempt)
            print(f"[RETRY] Attempt {attempt + 1} failed, retrying in {delay}s...")
            await asyncio.sleep(delay)

async def call_ollama_api(messages, temperature=0.8):
    """Call Ollama API with the given messages"""
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
    
    # Get the current model from settings manager
    current_model = settings_manager.get_setting_value('main_llm')
    if not current_model and LLM_PROVIDER == "ollama":
        # Fall back to environment variable if not set in runtime settings
        from config.settings import OLLAMA_MODEL
        current_model = OLLAMA_MODEL
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Convert messages to Ollama format
        # Ollama expects a single prompt, so we'll combine the messages
        system_message = ""
        conversation = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                conversation.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                conversation.append(f"Assistant: {msg['content']}")
        
        # Build the full prompt
        full_prompt = ""
        if system_message:
            full_prompt = f"{system_message}\n\n"
        full_prompt += "\n".join(conversation)
        if conversation and conversation[-1].startswith("User:"):
            full_prompt += "\nAssistant:"
        
        # Prepare Ollama API request
        data = {
            "model": current_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": OLLAMA_NUM_PREDICT,
                "top_k": OLLAMA_TOP_K,
                "top_p": OLLAMA_TOP_P,
                "repeat_penalty": OLLAMA_REPEAT_PENALTY,
            },
            "keep_alive": OLLAMA_KEEP_ALIVE
        }
        
        try:
            async with session.post(f"{OLLAMA_URL}/api/generate", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "")
                else:
                    error_text = await response.text()
                    print(f"Ollama API error: {response.status} - {error_text}")
                    return None
        except asyncio.TimeoutError:
            print(f"[ERROR] Ollama request timed out after {LLM_TIMEOUT} seconds")
            raise
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            raise

async def call_openrouter_api(messages, temperature=0.8, use_fallback=False):
    """Call OpenRouter API with the given messages, with optional fallback model"""
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
    
    # Determine which model to use - check runtime settings first
    if use_fallback:
        model_to_use = settings_manager.get_setting_value('fallback_llm')
        if not model_to_use:
            model_to_use = OPENROUTER_FALLBACK_MODEL
        print(f"[INFO] Using fallback model: {model_to_use}")
    else:
        model_to_use = settings_manager.get_setting_value('main_llm')
        if not model_to_use and LLM_PROVIDER == "openrouter":
            # Fall back to environment variable if not set in runtime settings
            from config.settings import OPENROUTER_MODEL
            model_to_use = OPENROUTER_MODEL
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        try:
            async with session.post(OPENROUTER_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    error_msg = f"OpenRouter API error with model {model_to_use}: {response.status} - {error_text}"
                    print(error_msg)
                    
                    # Check if we should try fallback
                    fallback_model = settings_manager.get_setting_value('fallback_llm') or OPENROUTER_FALLBACK_MODEL
                    if not use_fallback and fallback_model and response.status in [429, 500, 502, 503, 504]:
                        print(f"[INFO] Primary model failed with status {response.status}, attempting fallback...")
                        return await call_openrouter_api(messages, temperature, use_fallback=True)
                    
                    return None
        except asyncio.TimeoutError:
            print(f"[ERROR] OpenRouter request timed out after {LLM_TIMEOUT} seconds with model {model_to_use}")
            
            # Try fallback on timeout if available
            fallback_model = settings_manager.get_setting_value('fallback_llm') or OPENROUTER_FALLBACK_MODEL
            if not use_fallback and fallback_model:
                print(f"[INFO] Primary model timed out, attempting fallback...")
                return await call_openrouter_api(messages, temperature, use_fallback=True)
            
            raise
        except Exception as e:
            print(f"Error calling OpenRouter API with model {model_to_use}: {e}")
            
            # Try fallback on other errors if available
            fallback_model = settings_manager.get_setting_value('fallback_llm') or OPENROUTER_FALLBACK_MODEL
            if not use_fallback and fallback_model:
                print(f"[INFO] Primary model failed with error, attempting fallback...")
                return await call_openrouter_api(messages, temperature, use_fallback=True)
            
            raise

async def get_llm_reply(prompt, context=None, previous_message=None, room_id=None, url_contents=None, client=None):
    # Get comprehensive room context
    room_context = None
    if room_id:
        room_context = conversation_context.get_room_context(room_id, lookback_messages=MAX_CONTEXT_LOOKBACK)
    
    # Build context-aware system prompt
    system_prompt = BOT_PERSONALITY
    
    # Add price tracking capability to system prompt
    if ENABLE_PRICE_TRACKING:
        system_prompt += "\n\nYou have access to real-time cryptocurrency and fiat exchange rates. When users ask about prices, you can provide current market data including price, 24h change, and volume. You're knowledgeable about crypto markets, especially privacy coins like Monero."
    
    # Add rich context to system prompt
    if room_context:
        system_prompt += f"\n\n**ROOM CONTEXT**:\n"
        
        # Add topic context
        if room_context['top_topics']:
            topics_str = ', '.join([f"{topic} ({score:.1f})" for topic, score in room_context['top_topics'][:3]])
            system_prompt += f"Current hot topics: {topics_str}\n"
        
        # Add user expertise context
        if room_context['user_expertise']:
            system_prompt += "User expertise in the room:\n"
            for user, interests in list(room_context['user_expertise'].items())[:5]:
                system_prompt += f"  - {user}: {', '.join(interests)}\n"
        
        # Add conversation flow
        flow = room_context['conversation_flow']
        if 'dialogue' in flow:
            system_prompt += "This is a focused dialogue between two people. Be direct and helpful.\n"
        elif 'group_discussion' in flow:
            system_prompt += "This is a group discussion. Consider multiple perspectives.\n"
        
        if 'very_active' in flow:
            system_prompt += "The conversation is very active. Keep responses concise and on-point.\n"
        
        # Add recent important messages for context
        if room_context['recent_important']:
            system_prompt += "\nRecent important points:\n"
            for imp in room_context['recent_important'][-3:]:
                system_prompt += f"  - [{imp['type']}] {get_display_name(imp['sender'])}: {imp['body'][:100]}...\n"
    
    # Add URL content handling to system prompt
    if url_contents:
        system_prompt += "\n\nIMPORTANT: The user has shared URLs with content. Analyze and discuss the content thoroughly, providing insights, explanations, or help based on what you read."
    
    # Check if user is asking about the bot
    about_bot = any(keyword in prompt.lower() for keyword in ['who are you', 'what are you', 'your name'])
    
    if about_bot:
        prompt = f"{prompt}\n\n[Remember: You are Chatbot, a helpful assistant. Be self-aware about your identity.]"
    
    # Check for price-related questions
    price_keywords = ['price', 'cost', 'worth', 'value', 'exchange', 'convert', 'btc', 'eth', 'xmr', 'monero', 'bitcoin', 'ethereum', 'usd', 'eur', 'gbp']
    is_price_query = any(keyword in prompt.lower() for keyword in price_keywords)
    
    # If it's a price query, try to get price data
    if is_price_query and ENABLE_PRICE_TRACKING:
        price_info = await price_tracker.parse_price_request(prompt)
        if price_info:
            # Get the price data
            if price_info['type'] == 'crypto':
                price_data = await price_tracker.get_crypto_price(price_info['from'], price_info['to'])
                if price_data:
                    price_context = f"\n\n[CURRENT MARKET DATA: {price_info['from']} = {price_tracker.format_price(price_data['price'], price_info['to'])}"
                    if price_data.get('change_24h') is not None:
                        price_context += f", 24h change: {price_data['change_24h']:.2f}%"
                    price_context += "]"
                    prompt += price_context
            elif price_info['type'] == 'fiat':
                rate = await price_tracker.get_fiat_rate(price_info['from'], price_info['to'])
                if rate:
                    prompt += f"\n\n[CURRENT EXCHANGE RATE: 1 {price_info['from']} = {price_tracker.format_price(rate, price_info['to'])}]"
    
    # Check for technical questions or code
    is_technical = detect_code_in_message(prompt) or any(keyword in prompt.lower() for keyword in [
        'code', 'programming', 'debug', 'error', 'function', 'script', 'compile',
        'python', 'javascript', 'rust', 'linux', 'bash', 'git', 'docker',
        'api', 'database', 'sql', 'server', 'network', 'security'
    ])
    
    # Check for chat summary request
    summary_keywords = ['summary', 'summarize', 'recap', 'what happened', 'what was discussed', 'catch me up', 'tldr']
    wants_summary = any(keyword in prompt.lower() for keyword in summary_keywords)
    
    if wants_summary and room_id:
        # Extract time frame if specified
        minutes = 30  # default
        time_patterns = [
            (r'last (\d+) minutes?', 1),
            (r'past (\d+) minutes?', 1),
            (r'last (\d+) hours?', 60),
            (r'past (\d+) hours?', 60)
        ]
        
        for pattern, multiplier in time_patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                minutes = int(match.group(1)) * multiplier
                break
        
        chat_summary = create_comprehensive_summary(room_id, minutes)
        
        # Get LLM to enhance the summary - but don't include the internal prompt in the response
        prompt = f"The user asked for a summary. Based on the chat analysis, provide a natural, conversational summary focusing on key discussion points, questions asked and answered, action items, and the overall mood."
    
    # Filter the incoming prompt
    filtered_prompt = filter_bot_triggers(prompt)
    
    # If URL contents provided, add them to the prompt (with size limits)
    if url_contents:
        url_summary = "\n\n[SHARED CONTENT]:\n"
        for content in url_contents[:3]:  # Limit to 3 URLs
            url_summary += f"\nFrom {content['title']}:\n"
            
            if content['type'] == 'code':
                url_summary += f"Programming language: {content.get('language', 'unknown')}\n"
                url_summary += f"Code content:\n{content['content'][:2000]}\n"  # Limit content size
            else:
                url_summary += f"Content:\n{content['content'][:2000]}\n"  # Limit content size
        
        filtered_prompt = filtered_prompt + url_summary
    
    # Smart web search detection - check if web search is enabled
    should_search = False
    if not wants_summary and not about_bot and not url_contents and not is_price_query and settings_manager.is_web_search_enabled():
        should_search = await needs_web_search(filtered_prompt, room_context)
    
    # Search for technical docs if it's a technical question
    if is_technical and should_search and not url_contents:
        # Extract search query
        query = filtered_prompt
        for keyword in ['search for', 'look up', 'find', 'tell me about', 'what is', 'who is', 'how to', 'how do i']:
            if keyword in query.lower():
                query = query.lower().split(keyword)[-1].strip()
                break
        
        # Search technical resources
        results = await search_technical_docs(query)
        
        if results:
            search_summary = summarize_search_results(results, query)
            # Don't include the internal instructions in the prompt
            filtered_prompt = f"Based on search results about '{query}', provide a comprehensive technical answer with solutions, code examples if applicable, best practices, and alternative approaches."
            
    elif should_search:
        # Regular search for non-technical queries
        query = filtered_prompt
        for keyword in ['search for', 'look up', 'find', 'tell me about', 'what is', 'who is']:
            if keyword in query.lower():
                query = query.lower().split(keyword)[-1].strip()
                break
        
        # Use Jina search
        results = await search_with_jina(query)
        
        if results:
            search_summary = summarize_search_results(results, query)
            # Don't include the internal instructions in the prompt
            filtered_prompt = f"Based on search results about '{query}', provide a comprehensive but concise answer."
        else:
            filtered_prompt += "\n\n(Note: I couldn't retrieve web search results for this query, so I'll provide information based on my training data.)"
    
    # Build messages with context
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add technical context if needed
    if is_technical:
        messages[0]["content"] += "\n\nThe user has a technical question. Provide detailed, accurate technical help with code examples when appropriate. Be thorough but concise."
    
    # Add conversation history for better context
    if room_id and room_id in room_message_history:
        # Get last 10 messages for context
        recent_messages = list(room_message_history[room_id])[-10:]
        if len(recent_messages) > 3:
            context_messages = []
            for msg in recent_messages[:-1]:  # Exclude the current message
                role = "assistant" if msg['sender'] == (client.user_id if client else None) else "user"
                # Truncate long messages in context
                msg_content = msg['body'][:200] if len(msg['body']) > 200 else msg['body']
                context_messages.append({
                    "role": role,
                    "content": f"{get_display_name(msg['sender'])}: {msg_content}"
                })
            
            # Add only last 5 context messages
            messages.extend(context_messages[-5:])
    
    # Add previous message context if this is a reply
    if previous_message:
        messages.append({"role": "assistant", "content": f"[Previous message I sent]: {previous_message}"})
        messages.append({"role": "user", "content": f"[User is replying to the above message]: {filtered_prompt}"})
    else:
        messages.append({"role": "user", "content": filtered_prompt})
    
    # Adjust temperature based on context
    temperature = 0.7 if is_technical else 0.8
    
    # Use configured temperature for Ollama if using Ollama
    if LLM_PROVIDER == "ollama":
        temperature = OLLAMA_TEMPERATURE if not is_technical else min(0.7, OLLAMA_TEMPERATURE)
    
    try:
        # Call the appropriate LLM API based on configuration
        if LLM_PROVIDER == "ollama":
            reply = await call_ollama_api(messages, temperature)
            if reply is None:
                return "Hey, I hit a snag with the Ollama server. Mind trying again? 🔧"
        elif LLM_PROVIDER == "openrouter":
            if not OPENROUTER_API_KEY:
                return "Hey, OpenRouter isn't configured. Ask the admin to set it up! 🔧"
            reply = await call_openrouter_api(messages, temperature)
            if reply is None:
                return "Hey, I hit a snag with OpenRouter. Mind trying again? 🔧"
        else:
            return f"Hey, I don't know how to use the '{LLM_PROVIDER}' provider. Check the config! 🔧"
        
        # Filter the response
        filtered_reply = filter_bot_triggers(reply)
        
        return filtered_reply
        
    except asyncio.TimeoutError:
        print(f"[ERROR] LLM request timed out after {LLM_TIMEOUT} seconds")
        return "Yo, the AI servers are being slow af rn. Try again in a sec? 🔧"
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return f"Hmm, something went wonky on my end! Could you try that again? 🤔"
