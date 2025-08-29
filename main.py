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
# Get port from environment (for Render.com deployment)
    PORT = int(os.environ.get("PORT", 8000))
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

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
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask app on port {port}")
    logger.info(f"Bot @{bot.bot_username} is ready to receive messages")
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=debug)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot.stop_polling()
