#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot
"""

import asyncio
import logging
from bot import Bot
from web_server import run_web_server
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot and web server"""
    try:
        logger.info("Starting FileStore Bot...")

        # Start web server in a background thread
        web_thread = Thread(target=run_web_server, daemon=True)
        web_thread.start()
        logger.info("Web server running on port 8000")

        # Start bot
        bot = Bot()
        await bot.start()
        logger.info("Bot started successfully!")

        # Keep running
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
    
