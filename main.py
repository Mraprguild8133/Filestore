#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot
"""

import os
import asyncio
import logging
import threading
import signal
import sys
from flask import Flask, request
from bot import Bot  # Assuming you have a Bot class in bot.py

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global bot instance
bot_instance = None
bot_loop = None
bot_thread = None

async def setup_bot():
    """Set up the bot instance"""
    global bot_instance
    try:
        logger.info("Initializing FileStore Bot...")
        bot_instance = Bot()
        await bot_instance.initialize()  # Assuming your Bot class has an initialize method
        logger.info("Bot initialized successfully!")
        return bot_instance
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")
        raise

def run_bot():
    """Run the bot in a separate event loop"""
    global bot_instance, bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    
    try:
        bot_instance = bot_loop.run_until_complete(setup_bot())
        
        # Start the bot's polling or webhook setup
        logger.info("Starting bot polling...")
        bot_loop.run_until_complete(bot_instance.start_polling())  # or start_webhook()
    except Exception as e:
        logger.error(f"Error in bot thread: {e}")
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    finally:
        if bot_instance:
            bot_loop.run_until_complete(bot_instance.shutdown())
        bot_loop.close()

def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal")
    if bot_instance and bot_loop:
        # Schedule the shutdown coroutine in the bot's event loop
        future = asyncio.run_coroutine_threadsafe(bot_instance.shutdown(), bot_loop)
        future.result()  # Wait for shutdown to complete
    sys.exit(0)

@app.route('/')
def index():
    """Health check endpoint"""
    if bot_instance and bot_instance.is_running:
        return "Telegram FileStore Bot is running!"
    else:
        return "Telegram FileStore Bot is starting up...", 503

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram updates"""
    if bot_instance and bot_loop:
        try:
            # Process the update
            update = request.get_json()
            # Use the bot's event loop to process the update asynchronously
            asyncio.run_coroutine_threadsafe(
                bot_instance.process_update(update), 
                bot_loop
            )
            return "OK"
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return "Error processing update", 500
    return "Bot not initialized", 500

def main():
    """Main function to run the bot"""
    global bot_thread
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Get port from environment (for Render.com deployment)
    PORT = int(os.environ.get("PORT", 8000))
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    debug = ENVIRONMENT == "development"
    
    # Check if we should use webhook or polling
    USE_WEBHOOK = os.environ.get("USE_WEBHOOK", "false").lower() == "true"
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True  # Thread will exit when main thread exits
    bot_thread.start()
    
    logger.info(f"Starting Flask app on port {PORT}")
    
    try:
        # Start the Flask app (this runs in the main thread)
        app.run(host='0.0.0.0', port=PORT, debug=debug, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error starting Flask app: {e}")
    finally:
        # Wait for bot thread to finish if it's still running
        if bot_thread.is_alive():
            bot_thread.join(timeout=10)
        logger.info("Application stopped")

if __name__ == "__main__":
    main()
