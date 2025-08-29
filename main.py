#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for Telegram FileStore Bot + Web Server
"""

import asyncio
import logging
import os
import sys
from bot import Bot
from web_server import app
import uvicorn
from pyrogram.errors import SessionRevoked, AuthKeyUnregistered, AuthKeyInvalid, Unauthorized

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variable to hold the bot instance
bot_instance = None


def cleanup_session_files():
    """Remove all existing session files"""
    session_files = [f for f in os.listdir(".") if f.endswith(".session") or f.endswith(".session-journal")]
    for session_file in session_files:
        try:
            os.remove(session_file)
            logger.info(f"Deleted session file: {session_file}")
        except Exception as e:
            logger.error(f"Failed to delete {session_file}: {e}")
    return len(session_files) > 0


async def run_bot():
    """Start the Telegram bot with Pyrogram session handling"""
    global bot_instance
    
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting FileStore Bot (attempt {attempt + 1}/{max_retries})...")
            bot_instance = Bot()
            await bot_instance.start()
            logger.info("Bot started successfully!")
            
            # Keep bot alive until stopped
            await asyncio.Event().wait()
            return
            
        except (SessionRevoked, AuthKeyUnregistered, AuthKeyInvalid, Unauthorized) as e:
            logger.error(f"Session error: {e}")
            
            # Clean up session files on first attempt
            if attempt == 0:
                deleted = cleanup_session_files()
                if deleted:
                    logger.info("Session files removed. Please restart the bot to create a new session.")
                else:
                    logger.info("No session files found. Please configure the bot with a new session.")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Max retries exceeded. Bot cannot start without a valid session.")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error in bot: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Max retries exceeded due to unexpected errors.")
                raise


async def run_web():
    """Run Flask web server with uvicorn"""
    try:
        logger.info("Starting web server on port 8000...")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except Exception as e:
        logger.error(f"Error running web server: {e}")
        raise


async def shutdown(signal):
    """Cleanup tasks tied to the service's shutdown"""
    logger.info(f"Received exit signal {signal.name}...")
    
    if bot_instance:
        logger.info("Stopping bot...")
        await bot_instance.stop()
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Shutdown complete.")


async def main():
    """Run bot and web server together"""
    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for s in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(
            s, 
            lambda s=s: asyncio.create_task(shutdown(s))
        )
    
    try:
        await asyncio.gather(
            run_bot(),
            run_web()
        )
    except Exception as e:
        logger.error(f"Main application error: {e}")
        # Re-raise to ensure proper exit
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete.")
