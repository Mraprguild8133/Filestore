#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot
"""

import os
import asyncio
import logging
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
        asyncio.create_task(bot_instance.process_update(update))
        return "OK"
    return "Bot not initialized", 500

def main():
    """Main function to run the bot"""
    global bot_instance
    
    # Get port from environment (for Render.com deployment)
    PORT = int(os.environ.get("PORT", 8000))
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    debug = ENVIRONMENT == "development"
    
    # Set up the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_instance = loop.run_until_complete(setup_bot())
    
    logger.info(f"Starting Flask app on port {PORT}")
    logger.info(f"Bot @{bot_instance.bot_username} is ready to receive messages")
    
    try:
        # Start the Flask app
        app.run(host='0.0.0.0', port=PORT, debug=debug)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Clean up bot resources
        loop.run_until_complete(bot_instance.shutdown())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
