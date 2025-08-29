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
import time
from flask import Flask, request, jsonify

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
bot_initialized = False

async def setup_bot():
    """Set up the bot instance"""
    global bot_instance, bot_initialized
    try:
        logger.info("Initializing FileStore Bot...")
        
        # Import here to avoid circular imports
        from bot import Bot
        bot_instance = Bot()
        await bot_instance.initialize()
        
        bot_initialized = True
        logger.info("Bot initialized successfully!")
        return bot_instance
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot_initialized = False
        raise

def run_bot():
    """Run the bot in a separate event loop"""
    global bot_instance, bot_loop, bot_initialized
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    
    try:
        # Try to initialize the bot
        bot_instance = bot_loop.run_until_complete(setup_bot())
        
        if bot_initialized:
            # Start the bot's polling
            logger.info("Starting bot polling...")
            bot_loop.run_until_complete(bot_instance.start_polling())
        else:
            logger.error("Bot not initialized, cannot start polling")
            
    except ImportError as e:
        logger.error(f"Import error: {e}. Please check your bot.py file.")
    except Exception as e:
        logger.error(f"Unexpected error in bot thread: {e}")
        import traceback
        logger.error(traceback.format_exc())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    finally:
        if bot_instance and bot_initialized:
            try:
                bot_loop.run_until_complete(bot_instance.shutdown())
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        bot_loop.close()

def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal")
    if bot_instance and bot_loop and bot_initialized:
        try:
            # Schedule the shutdown coroutine in the bot's event loop
            future = asyncio.run_coroutine_threadsafe(bot_instance.shutdown(), bot_loop)
            future.result(timeout=10)  # Wait for shutdown to complete with timeout
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    sys.exit(0)

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler for Flask"""
    logger.error(f"Unhandled exception: {e}")
    import traceback
    logger.error(traceback.format_exc())
    return jsonify({"error": "Internal server error"}), 500

@app.route('/')
def index():
    """Health check endpoint"""
    try:
        if bot_initialized and hasattr(bot_instance, 'is_running') and bot_instance.is_running:
            return "Telegram FileStore Bot is running!"
        elif bot_initialized:
            return "Telegram FileStore Bot is initialized but not running"
        else:
            return "Telegram FileStore Bot is starting up...", 503
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "Error checking bot status", 500

@app.route('/health')
def health():
    """Simple health check endpoint"""
    return jsonify({"status": "ok", "bot_initialized": bot_initialized})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram updates"""
    try:
        if not bot_initialized or not bot_loop:
            return "Bot not initialized", 503
        
        # Process the update
        update = request.get_json()
        logger.info(f"Received webhook update: {update}")
        
        # Use the bot's event loop to process the update asynchronously
        asyncio.run_coroutine_threadsafe(
            bot_instance.process_update(update), 
            bot_loop
        )
        return "OK"
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return "Error processing update", 500

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
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, name="BotThread")
    bot_thread.daemon = True
    bot_thread.start()
    
    # Wait a moment for bot initialization
    time.sleep(2)
    
    logger.info(f"Starting Flask app on port {PORT}")
    logger.info(f"Bot initialized: {bot_initialized}")
    
    try:
        # Start the Flask app (this runs in the main thread)
        app.run(host='0.0.0.0', port=PORT, debug=debug, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error starting Flask app: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Wait for bot thread to finish if it's still running
        if bot_thread and bot_thread.is_alive():
            bot_thread.join(timeout=10)
        logger.info("Application stopped")

if __name__ == "__main__":
    main()
