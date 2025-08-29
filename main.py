#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Telegram FileStore Bot with Webhook support
"""

import asyncio
import logging
import signal
import os
import ssl
from aiohttp import web
from bot import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SignalHandler:
    """Handle shutdown signals gracefully"""
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_requested = True

class WebhookServer:
    """HTTP server for webhook handling"""
    def __init__(self, bot, host='0.0.0.0', port=8000):
        self.bot = bot
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Setup routes
        self.app.router.add_post('/webhook', self.handle_webhook)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/', self.handle_root)
    
    async def handle_webhook(self, request):
        """Handle Telegram webhook updates"""
        try:
            data = await request.json()
            await self.bot.process_update(data)
            return web.Response(text='OK')
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return web.Response(text='Error', status=500)
    
    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({"status": "healthy", "bot_running": self.bot.is_running})
    
    async def handle_root(self, request):
        """Root endpoint"""
        return web.Response(text="Telegram FileStore Bot Webhook Server")
    
    async def start(self):
        """Start the web server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Configure SSL if certificates are provided
        ssl_context = None
        ssl_cert = os.environ.get('SSL_CERTIFICATE')
        ssl_key = os.environ.get('SSL_PRIVATE_KEY')
        
        if ssl_cert and ssl_key:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(ssl_cert, ssl_key)
            logger.info("SSL context configured with provided certificates")
        
        self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=ssl_context)
        await self.site.start()
        logger.info(f"Webhook server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the web server"""
        if self.runner:
            await self.runner.cleanup()
        logger.info("Webhook server stopped")

async def main():
    """Main function to run the bot"""
    bot = None
    webhook_server = None
    signal_handler = SignalHandler()
    
    try:
        logger.info("Starting FileStore Bot...")
        
        # Initialize bot
        bot = Bot()
        await bot.initialize()
        
        # Check if webhook mode is enabled
        use_webhook = os.environ.get('USE_WEBHOOK', 'false').lower() == 'true'
        webhook_url = os.environ.get('WEBHOOK_URL')
        
        if use_webhook and webhook_url:
            logger.info("Starting in WEBHOOK mode")
            
            # Start webhook server
            webhook_server = WebhookServer(bot, port=8000)
            await webhook_server.start()
            
            # Set webhook
            await bot.set_webhook(webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
            
        else:
            logger.info("Starting in POLLING mode")
            await bot.start()
        
        logger.info("Bot started successfully!")
        
        # Keep the bot running until shutdown signal
        while not signal_handler.shutdown_requested:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Cleanup
        if bot:
            logger.info("Shutting down bot...")
            try:
                if use_webhook and webhook_url:
                    await bot.remove_webhook()
                await bot.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
        
        if webhook_server:
            logger.info("Stopping webhook server...")
            await webhook_server.stop()
        
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
