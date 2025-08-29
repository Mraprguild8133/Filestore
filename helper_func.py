#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions for the FileStore Bot
"""

import base64
import string
import random
import asyncio
import aiofiles
from typing import Union, List
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import Config
import logging

logger = logging.getLogger(__name__)

def encode(s: str) -> str:
    """Encode string to base64"""
    return base64.urlsafe_b64encode(s.encode("ascii")).decode("ascii")

def decode(s: str) -> str:
    """Decode base64 string"""
    return base64.urlsafe_b64decode(s.encode("ascii")).decode("ascii")

def get_readable_time(seconds: int) -> str:
    """Convert seconds to human readable time"""
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{int(period_value)}{period_name}")
    return ' '.join(result) if result else "0s"

def get_size(size: int) -> str:
    """Convert bytes to human readable size"""
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return f"{size:.2f} {units[i]}"

async def send_msg(user_id: int, message: Message, client: Client):
    """Send message to user with flood control"""
    try:
        await message.copy(chat_id=user_id)
        return 200, None
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await send_msg(user_id, message, client)
    except InputUserDeactivated:
        return 400, f"{user_id} : deactivated"
    except UserIsBlocked:
        return 400, f"{user_id} : blocked the bot"
    except Exception as e:
        return 500, f"{user_id} : {str(e)}"

def get_name(message: Message) -> str:
    """Get file name from message"""
    if message.document:
        return message.document.file_name
    elif message.video:
        return message.video.file_name or "video.mp4"
    elif message.audio:
        return message.audio.file_name or "audio.mp3"
    elif message.photo:
        return "photo.jpg"
    elif message.animation:
        return "animation.gif"
    elif message.voice:
        return "voice.ogg"
    elif message.video_note:
        return "video_note.mp4"
    elif message.sticker:
        return "sticker.webp"
    else:
        return "file"

def get_media_file_size(message: Message) -> int:
    """Get file size from message"""
    if message.document:
        return message.document.file_size
    elif message.video:
        return message.video.file_size
    elif message.audio:
        return message.audio.file_size
    elif message.photo:
        return message.photo.file_size
    elif message.animation:
        return message.animation.file_size
    elif message.voice:
        return message.voice.file_size
    elif message.video_note:
        return message.video_note.file_size
    elif message.sticker:
        return message.sticker.file_size
    else:
        return 0

def get_hash(media_msg: Message) -> str:
    """Generate unique hash for media"""
    if media_msg.document:
        return media_msg.document.file_unique_id
    elif media_msg.video:
        return media_msg.video.file_unique_id
    elif media_msg.audio:
        return media_msg.audio.file_unique_id
    elif media_msg.photo:
        return media_msg.photo.file_unique_id
    elif media_msg.animation:
        return media_msg.animation.file_unique_id
    elif media_msg.voice:
        return media_msg.voice.file_unique_id
    elif media_msg.video_note:
        return media_msg.video_note.file_unique_id
    elif media_msg.sticker:
        return media_msg.sticker.file_unique_id

def get_random_string(length: int = 8) -> str:
    """Generate random string"""
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

async def is_subscribed(client: Client, user_id: int, channels: List[int]) -> tuple:
    """Check if user is subscribed to channels"""
    if not channels:
        return True, None
    
    for channel_id in channels:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ["kicked", "left"]:
                channel = await client.get_chat(channel_id)
                return False, channel
        except Exception as e:
            logger.error(f"Error checking subscription for {channel_id}: {e}")
            continue
    
    return True, None

def get_file_type(message: Message) -> str:
    """Get file type from message"""
    if message.document:
        return "document"
    elif message.video:
        return "video"
    elif message.audio:
        return "audio"
    elif message.photo:
        return "photo"
    elif message.animation:
        return "animation"
    elif message.voice:
        return "voice"
    elif message.video_note:
        return "video_note"
    elif message.sticker:
        return "sticker"
    else:
        return "unknown"

async def get_verify_status(user_id: int) -> dict:
    """Get user verification status (placeholder for token verification)"""
    return {
        "is_verified": True,
        "verify_token": None,
        "link": None
    }

def get_start_message(first_name: str, user_id: int) -> str:
    """Get formatted start message"""
    return Config.START_MESSAGE.format(
        mention=f"[{first_name}](tg://user?id={user_id})",
        first_name=first_name,
        user_id=user_id,
        username="@" + first_name if first_name else f"User{user_id}"
    )
