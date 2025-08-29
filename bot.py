#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram FileStore Bot using Pyrogram
"""

import os
import asyncio
import logging
import signal
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from pyrogram.errors import SessionRevoked, Unauthorized
from config import Config
from database.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Bot(Client):
    def __init__(self):
        super().__init__(
            "FileStoreBot",  # session name
            api_id=Config.APP_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.TG_BOT_TOKEN,
            workers=20,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )
        self.db = Database()

    async def start(self):
        """Start the bot"""
        try:
            await super().start()
            me = await self.get_me()
            self.username = me.username
            self.first_name = me.first_name
            self.id = me.id

            await self.db.initialize(self)

            logger.info(f"✅ Bot started as @{self.username}")
            logger.info(f"🤖 Pyrogram v{__version__} (Layer {layer}) running")

        except (SessionRevoked, Unauthorized):
            logger.warning("⚠️ Session revoked or invalid. Deleting old session file...")

            # Remove invalid session files
            try:
                os.remove("FileStoreBot.session")
            except FileNotFoundError:
                pass

            # Restart clean
            await super().start()
            me = await self.get_me()
            self.username = me.username
            self.first_name = me.first_name
            self.id = me.id

            await self.db.initialize(self)

            logger.info(f"✅ New session created for @{self.username}")

        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}", exc_info=True)
            await self.stop()

    async def stop(self, *args):
        """Stop the bot"""
        await super().stop()
        logger.info("🛑 Bot stopped")


async def main():
    bot = Bot()

    # Handle signals for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))

    await bot.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
        
