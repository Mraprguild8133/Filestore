#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot + WebServer
"""

import asyncio
import logging
import threading
from bot import Bot
from webserver import app  # Import the Flask app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_webserver():
    """Run Flask web server on port 8000 in a separate thread"""
    logger.info("Starting WebServer on port 8000...")
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)


async def main():
    """Main function to run the bot and webserver"""
    try:
        logger.info("Starting FileStore Bot...")
        bot = Bot()
        await bot.start()
        logger.info("Bot started successfully!")

        # Start webserver in separate thread
        threading.Thread(target=run_webserver, daemon=True).start()

        # Keep bot running
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
    
