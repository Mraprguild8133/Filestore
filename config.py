#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for the FileStore Bot
"""

import os
from typing import List

class Config:
    # Required configuration
    API_HASH = os.getenv("API_HASH", "")
    APP_ID = int(os.getenv("APP_ID", "0"))
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    
    # Channel/Group configuration
    CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
    
    # Optional configuration
    ADMINS = []
    admin_list = os.getenv("ADMINS", "")
    if admin_list:
        ADMINS = [int(admin) for admin in admin_list.split()]
    
    # Add owner to admins if not already present
    if OWNER_ID and OWNER_ID not in ADMINS:
        ADMINS.append(OWNER_ID)
    
    # Bot configuration
    START_MESSAGE = os.getenv("START_MESSAGE", 
        "Hello {mention}\n\n"
        "I can store private files in a specified Channel and other users can access them from a special link.\n\n"
        "Send me any file to get started!")
    
    PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "False").lower() == "true"
    
    # Force subscription configuration
    FORCE_SUB_CHANNELS = []
    force_sub = os.getenv("FORCE_SUB_CHANNELS", "")
    if force_sub:
        FORCE_SUB_CHANNELS = [int(ch) for ch in force_sub.split()]
    
    # Auto delete configuration (in seconds)
    AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", "600"))  # 10 minutes default
    
    # Bot settings
    MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB
    
    # URLs and links
    PICS = [
        "https://telegra.ph/file/7e56d907542396289fee4.jpg",
        "https://telegra.ph/file/e4b465d8c7b67fda99094.jpg"
    ]
    
    # URL Shortener configuration
    SHORTENER_ENABLED = os.getenv("SHORTENER_ENABLED", "False").lower() == "true"
    SHORTENER_SITE = os.getenv("SHORTENER_SITE", "tinyurl.com")  # Default shortener
    SHORTENER_API_KEY = os.getenv("SHORTENER_API_KEY", "")
    
    # Supported shortener sites
    SUPPORTED_SHORTENERS = {
        "tinyurl.com": {"api_url": "https://tinyurl.com/api-create.php", "requires_key": False},
        "is.gd": {"api_url": "https://is.gd/create.php", "requires_key": False},
        "v.gd": {"api_url": "https://v.gd/create.php", "requires_key": False},
        "bit.ly": {"api_url": "https://api-ssl.bitly.com/v4/shorten", "requires_key": True},
        "short.io": {"api_url": "https://api.short.io/links", "requires_key": True},
        "rebrandly.com": {"api_url": "https://api.rebrandly.com/v1/links", "requires_key": True},
        "cutt.ly": {"api_url": "https://cutt.ly/api/api.php", "requires_key": True},
        "t.ly": {"api_url": "https://t.ly/api/v1/link/shorten", "requires_key": True},
        "gg.gg": {"api_url": "http://gg.gg/create", "requires_key": False},
        "tiny.cc": {"api_url": "https://tiny.cc/", "requires_key": True}
    }
    
    # Validation
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = {
            "API_HASH": cls.API_HASH,
            "APP_ID": cls.APP_ID,
            "TG_BOT_TOKEN": cls.TG_BOT_TOKEN,
            "OWNER_ID": cls.OWNER_ID,
            "CHANNEL_ID": cls.CHANNEL_ID
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

# Validate configuration on import
Config.validate()
