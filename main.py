#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot
"""

import os
import asyncio
import logging
import threading
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
    bot_instance = bot_loop.run_until_complete(setup_bot())
    
    # Start the bot's polling or webhook setup
    try:
        bot_loop.run_until_complete(bot_instance.start_polling())  # or start_webhook()
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    finally:
        bot_loop.run_until_complete(bot_instance.shutdown())
        bot_loop.close()

@app.route('/')
def index():
    """Health check endpoint"""
    return "Telegram FileStore Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram updates"""
    if bot_instance:
        # Process the update (this would need to be adapted to your bot's architecture)
        update = request.get_json()
        # Use the bot's event loop to process the update asynchronously
        asyncio.run_coroutine_threadsafe(
            bot_instance.process_update(update), 
            bot_loop
        )
        return "OK"
    return "Bot not initialized", 500

def main():
    """Main function to run the bot"""
    # Get port from environment (for Render.com deployment)
    PORT = int(os.environ.get("PORT", 8000))
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    debug = ENVIRONMENT == "development"
    
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
    finally:
        # Cleanup will happen automatically since bot_thread is daemonized
        pass

if __name__ == "__main__":
    main()
