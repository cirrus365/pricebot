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
    FILTERED_WORDS, ENABLE_PRICE_TRACKING, ENABLE_CONTEXT_ANALYSIS,
    ENABLE_WEB_SEARCH
)
from config.personality import BOT_PERSONALITY
from utils.helpers import filter_bot_triggers, get_display_name
from modules.context import room_message_history

# Import settings_manager to get runtime settings
from modules.settings_manager import settings_manager

async def get_llm_reply_with_retry(prompt, context=None, previous_message=None, room_id=None, url_contents=None, client=None):
    """Wrapper with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            return await get_llm_reply(prompt, context, previous_message, room_id, url_contents, client)
        except asyncio.TimeoutError:
            if attempt == MAX_RETRIES - 1:
                return "The AI servers are timing out. Please try again."
            await asyncio.sleep(BASE_RETRY_DELAY * (2 ** attempt))
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                return "Something went wrong. Please try again."
            await asyncio.sleep(BASE_RETRY_DELAY * (2 ** attempt))

async def call_ollama_api(messages, temperature=0.8):
    """Call Ollama API with the given messages"""
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
    
    current_model = settings_manager.get_setting_value('main_llm')
    if not current_model and LLM_PROVIDER == "ollama":
        from config.settings import OLLAMA_MODEL
        current_model = OLLAMA_MODEL
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Build simple prompt
        system_message = ""
        user_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                user_message = msg["content"]
        
        full_prompt = f"{system_message}\n\nUser: {user_message}\nAssistant:"
        
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
                    return None
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            raise

async def call_openrouter_api(messages, temperature=0.8, use_fallback=False):
    """Call OpenRouter API with the given messages"""
    timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
    
    if use_fallback:
        model_to_use = settings_manager.get_setting_value('fallback_llm') or OPENROUTER_FALLBACK_MODEL
    else:
        model_to_use = settings_manager.get_setting_value('main_llm')
        if not model_to_use and LLM_PROVIDER == "openrouter":
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
            "max_tokens": 500  # Reduced for faster responses
        }
        
        try:
            async with session.post(OPENROUTER_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    if not use_fallback and OPENROUTER_FALLBACK_MODEL and response.status in [429, 500, 502, 503, 504]:
                        return await call_openrouter_api(messages, temperature, use_fallback=True)
                    return None
        except asyncio.TimeoutError:
            if not use_fallback and OPENROUTER_FALLBACK_MODEL:
                return await call_openrouter_api(messages, temperature, use_fallback=True)
            raise
        except Exception as e:
            if not use_fallback and OPENROUTER_FALLBACK_MODEL:
                return await call_openrouter_api(messages, temperature, use_fallback=True)
            raise

async def get_llm_reply(prompt, context=None, previous_message=None, room_id=None, url_contents=None, client=None):
    # Build simple system prompt
    system_prompt = BOT_PERSONALITY
    
    # Add minimal context if enabled
    if ENABLE_CONTEXT_ANALYSIS and room_id and room_id in room_message_history:
        recent_messages = list(room_message_history[room_id])[-3:]  # Only last 3 messages
        if recent_messages:
            context_str = "\nRecent conversation:\n"
            for msg in recent_messages:
                context_str += f"- {get_display_name(msg['sender'])}: {msg['body'][:100]}\n"
            system_prompt += context_str
    
    # Add URL content if provided
    if url_contents:
        system_prompt += "\n\nThe user shared URLs. Analyze and discuss the content."
        url_summary = "\n\nShared content:\n"
        for content in url_contents[:1]:  # Only first URL
            url_summary += f"{content['title']}:\n{content['content'][:1000]}\n"
        prompt = prompt + url_summary
    
    # Check for price queries
    if ENABLE_PRICE_TRACKING:
        price_keywords = ['price', 'cost', 'worth', 'value', 'xmr', 'btc', 'eth']
        if any(keyword in prompt.lower() for keyword in price_keywords):
            from modules.price_tracker import price_tracker
            price_info = await price_tracker.parse_price_request(prompt)
            if price_info:
                if price_info['type'] == 'crypto':
                    price_data = await price_tracker.get_crypto_price(price_info['from'], price_info['to'])
                    if price_data:
                        prompt += f"\n[Current: {price_info['from']} = ${price_data['price']:.2f}]"
    
    # Simple web search if enabled
    if ENABLE_WEB_SEARCH and settings_manager.is_web_search_enabled():
        search_triggers = ['what is', 'who is', 'when did', 'where is', 'how to', 'latest', 'current', 'news']
        if any(trigger in prompt.lower() for trigger in search_triggers):
            from modules.web_search import search_with_jina
            query = prompt.split('?')[0] if '?' in prompt else prompt
            results = await search_with_jina(query, num_results=2)
            if results:
                prompt += "\n[Search results available - provide current information]"
    
    # Filter the prompt
    filtered_prompt = filter_bot_triggers(prompt)
    
    # Build messages
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    if previous_message:
        messages.append({"role": "assistant", "content": previous_message[:200]})
    
    messages.append({"role": "user", "content": filtered_prompt})
    
    # Call LLM
    try:
        if LLM_PROVIDER == "ollama":
            reply = await call_ollama_api(messages, temperature=0.8)
            if reply is None:
                return "Failed to get response from Ollama."
        elif LLM_PROVIDER == "openrouter":
            if not OPENROUTER_API_KEY:
                return "OpenRouter is not configured."
            reply = await call_openrouter_api(messages, temperature=0.8)
            if reply is None:
                return "Failed to get response from OpenRouter."
        else:
            return f"Unknown LLM provider: {LLM_PROVIDER}"
        
        # Filter and return
        return filter_bot_triggers(reply)
        
    except asyncio.TimeoutError:
        return "Response timed out. Please try again."
    except Exception as e:
        return "Something went wrong. Please try again."
