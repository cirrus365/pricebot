#!/usr/bin/env python3
"""
Nifty Bot - Multi-platform chatbot with Matrix, Discord, and Telegram support
Main entry point for the application
"""
import asyncio
import logging
import sys
from config.settings import INTEGRATIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main bot initialization and event loop"""
    tasks = []
    
    # Check which integrations are enabled
    matrix_enabled = INTEGRATIONS.get('matrix', True)
    discord_enabled = INTEGRATIONS.get('discord', False)
    telegram_enabled = INTEGRATIONS.get('telegram', False)
    
    print("\n" + "=" * 50)
    print("🚀 Nifty Bot Starting...")
    print("=" * 50)
    print(f"📡 Matrix Integration: {'✅ ENABLED' if matrix_enabled else '❌ DISABLED'}")
    print(f"💬 Discord Integration: {'✅ ENABLED' if discord_enabled else '❌ DISABLED'}")
    print(f"✈️ Telegram Integration: {'✅ ENABLED' if telegram_enabled else '❌ DISABLED'}")
    print("=" * 50 + "\n")
    
    # Start Matrix bot if enabled
    if matrix_enabled:
        logger.info("Starting Matrix integration...")
        from integrations.matrix_integration import run_matrix_bot
        tasks.append(asyncio.create_task(run_matrix_bot()))
    
    # Start Discord bot if enabled  
    if discord_enabled:
        logger.info("Starting Discord integration...")
        from integrations.discord_integration import run_discord_bot
        tasks.append(asyncio.create_task(run_discord_bot()))
    
    # Start Telegram bot if enabled
    if telegram_enabled:
        logger.info("Starting Telegram integration...")
        from integrations.telegram_integration import run_telegram_bot
        tasks.append(asyncio.create_task(run_telegram_bot()))
    
    if not tasks:
        logger.error("No integrations enabled! Enable at least one integration in .env file.")
        print("\n❌ ERROR: No integrations enabled!")
        print("Please set ENABLE_MATRIX=true, ENABLE_DISCORD=true, or ENABLE_TELEGRAM=true in your .env file")
        return
    
    # Wait for all tasks
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down...")
        print("\n\nShutting down Nifty Bot...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
