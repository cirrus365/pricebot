"""LLM interaction module"""
import asyncio
import aiohttp
import re
from datetime import datetime
from config.settings import (
    OPENROUTER_API_KEY, OPENROUTER_URL, LLM_TIMEOUT,
    MAX_RETRIES, BASE_RETRY_DELAY, MAX_CONTEXT_LOOKBACK, FILTERED_WORDS
)
from config.personality import BOT_PERSONALITY
from utils.helpers import filter_bot_triggers, get_display_name, detect_code_in_message
from utils.formatting import summarize_search_results
from modules.context import room_message_history, conversation_context, create_comprehensive_summary
from modules.web_search import needs_web_search, search_with_jina, search_technical_docs

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

async def get_llm_reply(prompt, context=None, previous_message=None, room_id=None, url_contents=None, client=None):
    # Get comprehensive room context
    room_context = None
    if room_id:
        room_context = conversation_context.get_room_context(room_id, lookback_messages=MAX_CONTEXT_LOOKBACK)
    
    # Build context-aware system prompt
    system_prompt = BOT_PERSONALITY
    
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
    about_nifty = any(keyword in prompt.lower() for keyword in ['who are you', 'what are you', 'your name', 'who is nifty', 'what is nifty'])
    
    if about_nifty:
        prompt = f"{prompt}\n\n[Remember: You are Nifty, a Matrix bot with the handle @nifty:matrix.stargazypie.xyz. Be self-aware about your identity.]"
    
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
        
        # Get LLM to enhance the summary
        enhanced_prompt = f"""The user asked: {prompt}

Here's the comprehensive analysis:
{chat_summary}

Based on this data, provide a natural, conversational summary. Focus on:
1. Key discussion points and decisions made
2. Questions that were asked and whether they were answered
3. Any action items or next steps mentioned
4. The overall mood and flow of the conversation

Keep your personality but be informative. Remember you are Nifty."""
        
        prompt = enhanced_prompt
    
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
    
    # Add timeout to the session
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Smart web search detection
        should_search = False
        if not wants_summary and not about_nifty and not url_contents:
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
                
                # Enhanced prompt for technical answers
                enhanced_prompt = f"""User asked a technical question: {filtered_prompt}

{search_summary}

Based on these search results, provide a comprehensive technical answer. Include:
1. Direct solution to their problem
2. Code examples if applicable (properly formatted)
3. Best practices and common pitfalls
4. Alternative approaches if relevant

Remember to maintain your personality while being technically accurate and helpful. You are Nifty, a skilled technical expert."""
                
                filtered_prompt = enhanced_prompt
                
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
                
                # Enhanced prompt for better summarization
                enhanced_prompt = f"""User asked: {filtered_prompt}

{search_summary}

Based on these search results, provide a comprehensive but concise answer. Focus on:
1. Directly answering the user's question
2. Highlighting the most important/relevant information
3. Mentioning any interesting or surprising facts
4. Being accurate while maintaining your personality

Remember you are Nifty, be aware of your identity."""
                
                filtered_prompt = enhanced_prompt
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
        
        data = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        try:
            async with session.post(OPENROUTER_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    reply = result["choices"][0]["message"]["content"]
                    
                    # Filter the response
                    filtered_reply = filter_bot_triggers(reply)
                    
                    return filtered_reply
                else:
                    error_text = await response.text()
                    print(f"OpenRouter API error: {response.status} - {error_text}")
                    return f"Hey, I'm Nifty and I hit a snag (error {response.status}). Mind trying again? 🔧"
        
        except asyncio.TimeoutError:
            print(f"[ERROR] LLM request timed out after {LLM_TIMEOUT} seconds")
            return "Yo, the AI servers are being slow af rn. Try again in a sec? 🔧"
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return f"Hmm, Nifty here - something went wonky on my end! Could you try that again? 🤔"
