#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram FileStore Bot using Pyrogram
"""

import os
import asyncio
import logging
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from database.database import Database

logger = logging.getLogger(__name__)

class Bot(Client):
    def __init__(self):
        super().__init__(
            "FileStoreBot",
            api_id=Config.APP_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.TG_BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )
        
        # Initialize in-memory database
        self.db = Database()
        
    async def start(self):
        """Start the bot"""
        await super().start()
        
        # Get bot info
        me = await self.get_me()
        self.username = me.username
        self.first_name = me.first_name
        self.id = me.id
        
        # Initialize database with bot info
        await self.db.initialize(self)
        
        logger.info(f"Bot started as @{self.username}")
        logger.info(f"Pyrogram v{__version__} (Layer {layer}) started on {me.first_name}")
        
    async def stop(self, *args):
        """Stop the bot"""
        await super().stop()
        logger.info("Bot stopped")
