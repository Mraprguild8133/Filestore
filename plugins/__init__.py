#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugins package for FileStore Bot
"""

import os
import importlib
import logging

logger = logging.getLogger(__name__)

# List of plugin modules to load
PLUGINS = [
    "start",
    "admin", 
    "genlink",
    "batch",
    "channel_post",
    "broadcast",
    "force_sub"
]

def load_plugins():
    """Load all plugins"""
    loaded_plugins = []
    
    for plugin in PLUGINS:
        try:
            module = importlib.import_module(f"plugins.{plugin}")
            loaded_plugins.append(plugin)
            logger.info(f"Loaded plugin: {plugin}")
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin}: {e}")
    
    logger.info(f"Successfully loaded {len(loaded_plugins)} plugins")
    return loaded_plugins

# Auto-load plugins when package is imported
load_plugins()
