#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In-memory database for the FileStore Bot
"""

import asyncio
import time
from typing import Dict, List, Set, Optional
from pyrogram import Client
from pyrogram.types import Message
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # User data
        self.users: Set[int] = set()
        self.banned_users: Set[int] = set()
        self.admins: Set[int] = set()
        
        # File storage
        self.files: Dict[str, Dict] = {}  # file_id -> file_data
        self.user_files: Dict[int, List[str]] = {}  # user_id -> [file_ids]
        
        # Batch storage
        self.batches: Dict[str, Dict] = {}  # batch_id -> batch_data
        
        # Force subscription channels
        self.force_sub_channels: Set[int] = set()
        self.force_sub_enabled: bool = True
        
        # Auto delete settings
        self.auto_delete_time: int = 600  # 10 minutes default
        self.auto_delete_enabled: bool = True
        
        # Bot statistics
        self.start_time: float = time.time()
        self.total_files: int = 0
        self.total_batches: int = 0
        
        # Bot instance
        self.bot: Optional[Client] = None
        
    async def initialize(self, bot: Client):
        """Initialize database with bot instance"""
        self.bot = bot
        
        # Load admins from config
        from config import Config
        self.admins.update(Config.ADMINS)
        self.force_sub_channels.update(Config.FORCE_SUB_CHANNELS)
        self.auto_delete_time = Config.AUTO_DELETE_TIME
        
        logger.info(f"Database initialized with {len(self.admins)} admins")
    
    # User management
    async def add_user(self, user_id: int):
        """Add user to database"""
        self.users.add(user_id)
        if user_id not in self.user_files:
            self.user_files[user_id] = []
    
    async def remove_user(self, user_id: int):
        """Remove user from database"""
        self.users.discard(user_id)
        if user_id in self.user_files:
            del self.user_files[user_id]
    
    async def get_all_users(self) -> List[int]:
        """Get all users"""
        return list(self.users)
    
    async def get_users_count(self) -> int:
        """Get total users count"""
        return len(self.users)
    
    async def is_user_exist(self, user_id: int) -> bool:
        """Check if user exists"""
        return user_id in self.users
    
    # Ban management
    async def ban_user(self, user_id: int):
        """Ban a user"""
        self.banned_users.add(user_id)
    
    async def unban_user(self, user_id: int):
        """Unban a user"""
        self.banned_users.discard(user_id)
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        return user_id in self.banned_users
    
    async def get_banned_users(self) -> List[int]:
        """Get all banned users"""
        return list(self.banned_users)
    
    # Admin management
    async def add_admin(self, user_id: int):
        """Add admin"""
        self.admins.add(user_id)
    
    async def remove_admin(self, user_id: int):
        """Remove admin"""
        self.admins.discard(user_id)
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.admins
    
    async def get_all_admins(self) -> List[int]:
        """Get all admins"""
        return list(self.admins)
    
    # File management
    async def save_file(self, file_id: str, file_data: Dict) -> str:
        """Save file and return unique ID"""
        unique_id = f"file_{int(time.time())}_{len(self.files)}"
        
        self.files[unique_id] = {
            **file_data,
            'created_at': time.time(),
            'access_count': 0
        }
        
        # Add to user files
        user_id = file_data.get('user_id')
        if user_id:
            if user_id not in self.user_files:
                self.user_files[user_id] = []
            self.user_files[user_id].append(unique_id)
        
        self.total_files += 1
        return unique_id
    
    async def get_file(self, file_id: str) -> Optional[Dict]:
        """Get file by ID"""
        file_data = self.files.get(file_id)
        if file_data:
            # Increment access count
            file_data['access_count'] += 1
        return file_data
    
    async def delete_file(self, file_id: str):
        """Delete file"""
        if file_id in self.files:
            file_data = self.files[file_id]
            user_id = file_data.get('user_id')
            
            # Remove from user files
            if user_id and user_id in self.user_files:
                if file_id in self.user_files[user_id]:
                    self.user_files[user_id].remove(file_id)
            
            del self.files[file_id]
    
    async def get_user_files(self, user_id: int) -> List[Dict]:
        """Get all files for a user"""
        if user_id not in self.user_files:
            return []
        
        user_file_ids = self.user_files[user_id]
        return [self.files[fid] for fid in user_file_ids if fid in self.files]
    
    # Batch management
    async def save_batch(self, batch_id: str, batch_data: Dict) -> str:
        """Save batch"""
        unique_id = f"batch_{int(time.time())}_{len(self.batches)}"
        
        self.batches[unique_id] = {
            **batch_data,
            'created_at': time.time(),
            'access_count': 0
        }
        
        self.total_batches += 1
        return unique_id
    
    async def get_batch(self, batch_id: str) -> Optional[Dict]:
        """Get batch by ID"""
        batch_data = self.batches.get(batch_id)
        if batch_data:
            # Increment access count
            batch_data['access_count'] += 1
        return batch_data
    
    async def delete_batch(self, batch_id: str):
        """Delete batch"""
        if batch_id in self.batches:
            del self.batches[batch_id]
    
    # Force subscription management
    async def add_force_sub_channel(self, channel_id: int):
        """Add force subscription channel"""
        self.force_sub_channels.add(channel_id)
    
    async def remove_force_sub_channel(self, channel_id: int):
        """Remove force subscription channel"""
        self.force_sub_channels.discard(channel_id)
    
    async def get_force_sub_channels(self) -> List[int]:
        """Get all force subscription channels"""
        return list(self.force_sub_channels)
    
    async def set_force_sub_enabled(self, enabled: bool):
        """Enable/disable force subscription"""
        self.force_sub_enabled = enabled
    
    async def is_force_sub_enabled(self) -> bool:
        """Check if force subscription is enabled"""
        return self.force_sub_enabled
    
    # Auto delete management
    async def set_auto_delete_time(self, seconds: int):
        """Set auto delete time"""
        self.auto_delete_time = seconds
    
    async def get_auto_delete_time(self) -> int:
        """Get auto delete time"""
        return self.auto_delete_time
    
    async def set_auto_delete_enabled(self, enabled: bool):
        """Enable/disable auto delete"""
        self.auto_delete_enabled = enabled
    
    async def is_auto_delete_enabled(self) -> bool:
        """Check if auto delete is enabled"""
        return self.auto_delete_enabled
    
    # Statistics
    async def get_stats(self) -> Dict:
        """Get bot statistics"""
        uptime = time.time() - self.start_time
        
        return {
            'total_users': len(self.users),
            'total_banned': len(self.banned_users),
            'total_admins': len(self.admins),
            'total_files': self.total_files,
            'total_batches': self.total_batches,
            'current_files': len(self.files),
            'current_batches': len(self.batches),
            'uptime': uptime,
            'force_sub_channels': len(self.force_sub_channels),
            'force_sub_enabled': self.force_sub_enabled,
            'auto_delete_time': self.auto_delete_time,
            'auto_delete_enabled': self.auto_delete_enabled
        }
    
    # Cleanup tasks
    async def cleanup_expired_files(self):
        """Remove expired files based on auto delete time"""
        if not self.auto_delete_enabled:
            return
        
        current_time = time.time()
        expired_files = []
        
        for file_id, file_data in self.files.items():
            if current_time - file_data['created_at'] > self.auto_delete_time:
                expired_files.append(file_id)
        
        for file_id in expired_files:
            await self.delete_file(file_id)
            logger.info(f"Auto-deleted expired file: {file_id}")
        
        return len(expired_files)
    
    async def cleanup_expired_batches(self):
        """Remove expired batches based on auto delete time"""
        if not self.auto_delete_enabled:
            return
        
        current_time = time.time()
        expired_batches = []
        
        for batch_id, batch_data in self.batches.items():
            if current_time - batch_data['created_at'] > self.auto_delete_time:
                expired_batches.append(batch_id)
        
        for batch_id in expired_batches:
            await self.delete_batch(batch_id)
            logger.info(f"Auto-deleted expired batch: {batch_id}")
        
        return len(expired_batches)
    
    async def start_cleanup_task(self):
        """Start periodic cleanup task"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                deleted_files = await self.cleanup_expired_files()
                deleted_batches = await self.cleanup_expired_batches()
                
                if deleted_files or deleted_batches:
                    logger.info(f"Cleanup completed: {deleted_files} files, {deleted_batches} batches deleted")
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
