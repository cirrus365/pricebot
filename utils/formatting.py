"""Message formatting utilities"""
import re
import html

def format_code_blocks(text):
    """Format code blocks properly for Matrix markdown"""
    # Pattern to match code blocks with language hints
    code_block_pattern = r'```(\w*)\n(.*?)```'
    
    def replace_code_block(match):
        language = match.group(1) or 'text'
        code = match.group(2)
        return f'<pre><code class="language-{language}">{html.escape(code)}</code></pre>'
    
    # Replace code blocks
    formatted = re.sub(code_block_pattern, replace_code_block, text, flags=re.DOTALL)
    
    # Handle inline code
    inline_pattern = r'`([^`]+)`'
    formatted = re.sub(inline_pattern, r'<code>\1</code>', formatted)
    
    return formatted

def extract_code_from_response(response):
    """Extract code blocks from LLM response and format them separately"""
    parts = []
    current_pos = 0
    
    # Find all code blocks
    code_block_pattern = r'```(\w*)\n(.*?)```'
    
    for match in re.finditer(code_block_pattern, response, re.DOTALL):
        # Add text before code block
        if match.start() > current_pos:
            text_part = response[current_pos:match.start()].strip()
            if text_part:
                parts.append({
                    'type': 'text',
                    'content': text_part
                })
        
        # Add code block
        language = match.group(1) or 'text'
        code = match.group(2).strip()
        
        parts.append({
            'type': 'code',
            'language': language,
            'content': code
        })
        
        current_pos = match.end()
    
    # Add remaining text
    if current_pos < len(response):
        text_part = response[current_pos:].strip()
        if text_part:
            parts.append({
                'type': 'text',
                'content': text_part
            })
    
    return parts if parts else [{'type': 'text', 'content': response}]

def summarize_search_results(results, query):
    """Create a better summary of search results"""
    if not results:
        return None
    
    summary = f"🔍 Search results for '{query}':\n\n"
    
    for i, result in enumerate(results, 1):
        summary += f"**{i}. {result['title']}**\n"
        summary += f"   {result['snippet']}\n"
        if result.get('url'):
            summary += f"   🔗 {result.get('url', '')}\n"
        summary += "\n"
    
    return summary
