"""
Discord integration for Price Tracker & World Clock Bot
"""
import discord
from discord.ext import commands
import asyncio
import logging
from config.settings import DISCORD_TOKEN, BOT_USERNAME, ENABLE_PRICE_TRACKING, ENABLE_STOCK_MARKET

logger = logging.getLogger(__name__)

class PriceTrackerDiscordBot(commands.Bot):
    """Discord bot implementation for Price Tracker & World Clock"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        
        super().__init__(
            command_prefix='?',
            intents=intents,
            description=f"{BOT_USERNAME.capitalize()} - Price tracking and world clock bot",
            help_command=None  # Disable default help command to use our custom one
        )
        
    async def setup_hook(self):
        """Initialize bot on startup"""
        await self.add_cog(PriceCommands(self))
        logger.info("Discord bot setup complete")
        
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'Discord bot logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="crypto prices | ?help"
            )
        )

class PriceCommands(commands.Cog):
    """Command handlers for Price Tracker & World Clock Discord bot"""
    
    def __init__(self, bot):
        self.bot = bot
        # Import here to avoid circular imports
        from modules.price_tracker import price_tracker
        from modules.stock_tracker import stock_tracker
        from modules.world_clock import world_clock
        self.price_tracker = price_tracker
        self.stock_tracker = stock_tracker
        self.world_clock = world_clock
        
    @commands.command(name='help', help='Show this help message')
    async def help_command(self, ctx):
        """Custom help command"""
        embed = discord.Embed(
            title=f"💰 Price Tracker & World Clock Bot Commands",
            description="Track cryptocurrency, stock prices, and world time!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Price Commands",
            value="`?price <crypto> [currency]` - Get crypto prices\n`?price <from> <to>` - Get exchange rates\n`?xmr` - Get Monero price",
            inline=False
        )
        
        embed.add_field(
            name="📊 Stock Market",
            value="`?stonks <ticker>` - Get stock information\n`?stonks` - Get market summary",
            inline=False
        )
        
        embed.add_field(
            name="🕐 World Clock",
            value="`?clock <city/country>` - Get time for a location\n`?clock` - Show current UTC time",
            inline=False
        )
        
        embed.add_field(
            name="📊 Info",
            value="`?help` - Show this message\n`?ping` - Check bot latency",
            inline=False
        )
        
        embed.set_footer(text=f"Price Tracker & World Clock Bot")
        await ctx.send(embed=embed)
        
    @commands.command(name='clock', help='Get time for a city or country')
    async def clock_command(self, ctx, *, location: str = None):
        """Get world clock time"""
        async with ctx.typing():
            query = location if location else ""
            response = await self.world_clock.handle_clock_command(query)
            
            # Create embed
            embed = discord.Embed(
                title="🕐 World Clock",
                description=response,
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
        
    @commands.command(name='stonks', help='Get stock market information')
    async def stonks_command(self, ctx, *, ticker: str = None):
        """Get stock market data"""
        if not ENABLE_STOCK_MARKET:
            await ctx.send("Stock tracking feature is not enabled.")
            return
        
        async with ctx.typing():
            if not ticker:
                # Get market summary
                response = await self.stock_tracker.get_market_summary()
            else:
                # Get specific stock info
                response = await self.stock_tracker.get_stock_info(ticker)
            
            # Create embed
            embed = discord.Embed(
                title="📊 Stock Market Data",
                description=response,
                color=discord.Color.green() if "📈" in response else discord.Color.red()
            )
            
            await ctx.send(embed=embed)
        
    @commands.command(name='price', help='Get cryptocurrency prices or exchange rates')
    async def price_command(self, ctx, *, query: str = "XMR"):
        """Get cryptocurrency price or exchange rate"""
        if not ENABLE_PRICE_TRACKING:
            await ctx.send("Price tracking feature is not enabled.")
            return
        
        async with ctx.typing():
            response = await self.price_tracker.get_price_response(f"price {query}")
            if response:
                embed = discord.Embed(
                    title=f"💰 Price Information",
                    description=response,
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Couldn't fetch price for {query}")
                
    @commands.command(name='xmr', help='Get Monero price')
    async def xmr_command(self, ctx):
        """Quick command for Monero price"""
        if not ENABLE_PRICE_TRACKING:
            await ctx.send("Price tracking feature is not enabled.")
            return
        
        await self.price_command(ctx, query="XMR")
        
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
        
    bot = PriceTrackerDiscordBot()
    
    print("=" * 50)
    print(f"💰 Price Tracker & World Clock Bot - Discord Integration Active!")
    print("=" * 50)
    print("✅ Discord bot starting...")
    print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
    print("📝 Commands: Use ? prefix (e.g., ?help)")
    print("💰 Price tracking: ?price <crypto> [currency] or ?price <from> <to>")
    print("📊 Stock market: ?stonks <ticker> for stock data")
    print("🕐 World clock: ?clock <location> for time info")
    print("=" * 50)
    
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Discord bot error: {e}")
        await bot.close()
        raise
