#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot
"""

import asyncio
import logging
from bot import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot"""
    try:
        logger.info("Starting FileStore Bot...")
        bot = Bot()
        await bot.start()
        logger.info("Bot started successfully!")
        await asyncio.Event().wait()  # Keep the bot running
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
