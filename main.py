#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web server entry point for Telegram FileStore Bot
Runs on port 8000 and supports webhook handling
"""
import Pyrogram
import asyncio
import logging
import os
from flask import Flask, request
from bot import Bot

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Global bot instance
bot_instance: Bot | None = None

@app.route("/", methods=["GET"])
def home():
    return "✅ FileStore Bot is running!", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming webhook updates from Telegram"""
    if bot_instance is None:
        return "❌ Bot not initialized", 500

    try:
        update = request.get_json(force=True)
        asyncio.run(bot_instance.process_update(update))
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500


async def start_bot():
    """Start bot in polling mode once, then switch to webhook"""
    global bot_instance
    logger.info("Starting FileStore Bot in polling mode...")
    bot_instance = Bot()
    await bot_instance.start()   # Your Bot should internally setup dispatcher/handlers
    logger.info("Bot started successfully in polling mode!")


def run():
    """Run Flask server on port 8000"""
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    try:
        # First run: polling
        asyncio.run(start_bot())

        # Then: web server for webhook
        logger.info("Starting Flask web server for webhook...")
        run()

    except Exception as e:
        logger.error(f"Error running web server: {e}")
