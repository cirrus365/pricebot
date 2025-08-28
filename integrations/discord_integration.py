"""
Discord integration for Chatbot
"""
import discord
from discord.ext import commands
import asyncio
from typing import Optional
import logging
from config.settings import DISCORD_TOKEN, DISCORD_COMMAND_PREFIX, DISCORD_ALLOWED_GUILDS, BOT_USERNAME, ENABLE_MEME_GENERATION
from config.personality import BOT_PERSONALITY
from modules.llm import get_llm_reply
from modules.price_tracker import price_tracker
from modules.web_search import search_with_jina, fetch_url_content
from modules.meme_generator import meme_generator
from utils.formatting import format_code_blocks
from utils.helpers import extract_urls_from_message, detect_code_in_message

logger = logging.getLogger(__name__)

class ChatbotDiscordBot(commands.Bot):
    """Discord bot implementation for Chatbot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        
        super().__init__(
            command_prefix=DISCORD_COMMAND_PREFIX,
            intents=intents,
            description=f"{BOT_USERNAME.capitalize()} - Your digital assistant"
        )
        
        self.conversation_history = {}  # channel_id -> list of messages
        self.max_history = 20
        
    async def setup_hook(self):
        """Initialize bot on startup"""
        await self.add_cog(ChatbotCommands(self))
        logger.info("Discord bot setup complete")
        
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'Discord bot logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="your questions | !help"
            )
        )
        
    async def on_guild_join(self, guild):
        """Handle joining a new guild"""
        if DISCORD_ALLOWED_GUILDS and str(guild.id) not in DISCORD_ALLOWED_GUILDS:
            logger.warning(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()
            return
            
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore bot's own messages
        if message.author == self.user:
            return
            
        # Check if in allowed guild
        if message.guild and DISCORD_ALLOWED_GUILDS:
            if str(message.guild.id) not in DISCORD_ALLOWED_GUILDS:
                return
                
        # Store message in history
        channel_id = message.channel.id
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []
            
        self.conversation_history[channel_id].append({
            'author': message.author.name,
            'content': message.content,
            'timestamp': message.created_at
        })
        
        # Trim history
        if len(self.conversation_history[channel_id]) > self.max_history:
            self.conversation_history[channel_id] = self.conversation_history[channel_id][-self.max_history:]
            
        # Process commands
        await self.process_commands(message)
        
        # Check if bot was mentioned or replied to
        if self.user in message.mentions or message.reference:
            await self.handle_mention(message)
            
    async def handle_mention(self, message):
        """Handle when bot is mentioned"""
        async with message.channel.typing():
            # Clean message content
            content = message.content.replace(f'<@{self.user.id}>', '').strip()
            
            if not content:
                await message.reply("Hey! What's up? Ask me something!")
                return
                
            # Get conversation context
            context = self.get_conversation_context(message.channel.id)
            
            # Check for URLs in message
            urls = extract_urls_from_message(content)
            url_contents = None
            if urls:
                url_contents = []
                for url in urls[:2]:  # Limit to 2 URLs
                    url_content = await fetch_url_content(url)
                    if url_content:
                        url_contents.append(url_content)
                        
            # Check if web search is needed
            if any(keyword in content.lower() for keyword in ['search', 'find', 'look up', 'what is', 'who is']):
                search_results = await search_with_jina(content, num_results=3)
                if search_results:
                    context += f"\n\nSearch results:\n{search_results}"
                    
            # Get LLM response
            try:
                response = await get_llm_reply(
                    prompt=content,
                    context=context,
                    url_contents=url_contents
                )
                
                # Format response
                if detect_code_in_message(response):
                    response = format_code_blocks(response)
                    
                # Split long messages
                if len(response) > 2000:
                    chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                    for chunk in chunks:
                        await message.reply(chunk)
                else:
                    await message.reply(response)
                    
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await message.reply("Oops! Something went wrong. Try again later!")
                
    def get_conversation_context(self, channel_id):
        """Get conversation context for a channel"""
        if channel_id not in self.conversation_history:
            return ""
            
        context_messages = []
        for msg in self.conversation_history[channel_id][-10:]:  # Last 10 messages
            context_messages.append(f"{msg['author']}: {msg['content']}")
            
        return "\n".join(context_messages)

class ChatbotCommands(commands.Cog):
    """Command handlers for Chatbot Discord bot"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name='help', help='Show this help message')
    async def help_command(self, ctx):
        """Custom help command"""
        embed = discord.Embed(
            title=f"{BOT_USERNAME.capitalize()} Bot Commands",
            description="Here's what I can do!",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="💬 Chat",
            value="Just mention me or reply to my messages!",
            inline=False
        )
        
        embed.add_field(
            name="💰 Price Commands",
            value="`!price <crypto>` - Get crypto prices\n`!xmr` - Get Monero price",
            inline=False
        )
        
        if ENABLE_MEME_GENERATION:
            embed.add_field(
                name="🎨 Meme Generation",
                value="`!meme <topic>` - Generate a meme with AI captions",
                inline=False
            )
        
        embed.add_field(
            name="🔍 Search",
            value="Ask me to search for anything!",
            inline=False
        )
        
        embed.add_field(
            name="📊 Info",
            value="`!stats` - Bot statistics\n`!ping` - Check bot latency",
            inline=False
        )
        
        embed.set_footer(text=f"Made with 💜 by the {BOT_USERNAME.capitalize()} team")
        await ctx.send(embed=embed)
        
    @commands.command(name='meme', help='Generate a meme with AI captions')
    async def meme_command(self, ctx, *, topic: str = None):
        """Generate a meme based on user input"""
        if not ENABLE_MEME_GENERATION:
            await ctx.send("Meme generation is currently disabled.")
            return
            
        if not topic:
            await ctx.send("Please provide a topic for the meme. Usage: `!meme <topic>`")
            return
            
        async with ctx.typing():
            # Generate the meme
            meme_url, caption = await meme_generator.handle_meme_command(f"!meme {topic}")
            
            if meme_url:
                # Create embed with meme
                embed = discord.Embed(
                    title="🎨 Generated Meme",
                    description=caption,
                    color=discord.Color.green()
                )
                embed.set_image(url=meme_url)
                embed.set_footer(text=f"Topic: {topic}")
                await ctx.send(embed=embed)
            else:
                await ctx.send(caption or "Failed to generate meme. Please try again.")
        
    @commands.command(name='price', help='Get cryptocurrency prices')
    async def price_command(self, ctx, *, crypto: str = "XMR"):
        """Get cryptocurrency price"""
        async with ctx.typing():
            response = await price_tracker.get_price_response(f"price {crypto}")
            if response:
                embed = discord.Embed(
                    title=f"💰 {crypto.upper()} Price",
                    description=response,
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Couldn't fetch price for {crypto}")
                
    @commands.command(name='xmr', help='Get Monero price')
    async def xmr_command(self, ctx):
        """Quick command for Monero price"""
        await self.price_command(ctx, crypto="XMR")
        
    @commands.command(name='stats', help='Show bot statistics')
    async def stats_command(self, ctx):
        """Show bot statistics"""
        embed = discord.Embed(
            title=f"📊 {BOT_USERNAME.capitalize()} Bot Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Servers",
            value=len(self.bot.guilds),
            inline=True
        )
        
        embed.add_field(
            name="Channels",
            value=len(list(self.bot.get_all_channels())),
            inline=True
        )
        
        embed.add_field(
            name="Users",
            value=len(self.bot.users),
            inline=True
        )
        
        embed.add_field(
            name="Latency",
            value=f"{round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        await ctx.send(embed=embed)
        
    @commands.command(name='ping', help='Check bot latency')
    async def ping_command(self, ctx):
        """Check bot latency"""
        await ctx.send(f"🏓 Pong! Latency: {round(self.bot.latency * 1000)}ms")

async def run_discord_bot():
    """Run the Discord bot"""
    # Check for required Discord credentials
    if not DISCORD_TOKEN:
        logger.error("Discord token not configured. Please set DISCORD_TOKEN in .env file")
        print("\n❌ ERROR: Discord token missing!")
        print("Please configure DISCORD_TOKEN in your .env file")
        return
        
    bot = ChatbotDiscordBot()
    
    print("=" * 50)
    print(f"🤖 {BOT_USERNAME.capitalize()} Bot - Discord Integration Active!")
    print("=" * 50)
    print("✅ Discord bot starting...")
    print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
    print("📝 Commands: Use ! prefix (e.g., !help)")
    print("💬 Chat: Mention the bot or reply to its messages")
    print("💰 Price tracking: !price <crypto> or !xmr")
    if ENABLE_MEME_GENERATION:
        print("🎨 Meme generation: !meme <topic> to create memes")
    print("🔍 Web search: Ask to search for anything")
    print("📊 Stats: !stats for bot statistics")
    print("=" * 50)
    
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Discord bot error: {e}")
        await bot.close()
        raise
