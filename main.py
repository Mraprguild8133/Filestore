#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot
"""

import asyncio
import logging
from bot import Bot
from webserver import run_webserver
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot"""
    try:
        logger.info("Starting FileStore Bot...")

        # Start web server in a separate thread
        web_thread = Thread(target=run_webserver, daemon=True)
        web_thread.start()

        # Start Telegram bot
        bot = Bot()
        await bot.start()
        logger.info("Bot started successfully!")

        # Keep alive
        await asyncio.Event().wait()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
    
