#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for Telegram FileStore Bot + Web Server
"""

import asyncio
import logging
import os
from bot import Bot
from web_server import app
import uvicorn
from pyrogram.errors import SessionRevoked, AuthKeyUnregistered

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_bot():
    """Start the Telegram bot with Pyrogram session handling"""
    try:
        logger.info("Starting FileStore Bot...")
        bot = Bot()
        await bot.start()
        logger.info("Bot started successfully!")
        await asyncio.Event().wait()  # Keep bot alive
    except (SessionRevoked, AuthKeyUnregistered):
        logger.error("Telegram session revoked! Removing old session file...")
        # remove old session file
        for f in os.listdir("."):
            if f.endswith(".session"):
                try:
                    os.remove(f)
                    logger.info(f"Deleted old session file: {f}")
                except Exception as e:
                    logger.error(f"Failed to delete {f}: {e}")
        logger.info("Restart the bot to generate a new session.")
    except Exception as e:
        logger.error(f"Unexpected error in bot: {e}")
        raise


async def run_web():
    """Run Flask web server with uvicorn"""
    logger.info("Starting web server on port 8000...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Run bot and web server together"""
    await asyncio.gather(
        run_bot(),
        run_web()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    
