#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate link plugin for single posts
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from helper_func import encode, get_name, get_media_file_size, get_file_type, get_hash, get_size
from shortener import shortener
import re

logger = logging.getLogger(__name__)

# Admin filter
def admin_filter(_, __, message):
    return message.from_user.id in Config.ADMINS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("genlink") & admin_only)
async def genlink_command(client: Client, message: Message):
    """Generate link for a single post"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if await client.db.is_user_banned(user_id):
        await message.reply_text("⚠️ You are banned from using this bot!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/genlink <channel_post_link>`\n\n"
            "**Example:**\n"
            "`/genlink https://t.me/c/1234567890/123`\n"
            "`/genlink https://t.me/channel_username/123`\n\n"
            "📝 **Note:** Make sure I'm added as admin in the channel!"
        )
        return
    
    post_link = message.command[1]
    
    try:
        # Parse the post link
        channel_id, message_id = await parse_post_link(post_link)
        
        if not channel_id or not message_id:
            await message.reply_text("❌ Invalid post link format!")
            return
        
        # Get the message from channel
        try:
            channel_msg = await client.get_messages(channel_id, message_id)
        except Exception as e:
            await message.reply_text(f"❌ Error accessing the post: {str(e)}\n\nMake sure I'm added as admin in the channel!")
            return
        
        if not channel_msg:
            await message.reply_text("❌ Post not found!")
            return
        
        # Check if message has media
        if not (channel_msg.document or channel_msg.video or channel_msg.audio or 
                channel_msg.photo or channel_msg.animation or channel_msg.voice or 
                channel_msg.video_note or channel_msg.sticker):
            await message.reply_text("❌ The post doesn't contain any media file!")
            return
        
        # Prepare file data
        file_data = {
            'user_id': user_id,
            'channel_id': channel_id,
            'message_id': message_id,
            'file_name': get_name(channel_msg),
            'file_size': get_media_file_size(channel_msg),
            'file_type': get_file_type(channel_msg),
            'file_hash': get_hash(channel_msg),
            'post_link': post_link,
            'upload_date': channel_msg.date.strftime("%Y-%m-%d %H:%M:%S") if channel_msg.date else "Unknown"
        }
        
        # Add human readable file size
        file_data['file_size_human'] = get_size(file_data['file_size'])
        
        # Save file to database
        file_id = await client.db.save_file("", file_data)
        
        # Generate shareable link
        encoded_data = encode(file_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Apply URL shortener if enabled
        share_link = await shortener.shorten_url(share_link)
        
        # Create response
        response_text = f"""
✅ **Link Generated Successfully!**

📁 **File Name:** `{file_data['file_name']}`
📊 **File Size:** `{file_data['file_size_human']}`
📂 **File Type:** `{file_data['file_type'].title()}`
📅 **Date:** `{file_data['upload_date']}`

🔗 **Shareable Link:**
`{share_link}`

📋 **Quick Copy:**
{share_link}
"""
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open Link", url=share_link)],
            [
                InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_link_{encoded_data}"),
                InlineKeyboardButton("📤 Share", switch_inline_query=share_link)
            ],
            [InlineKeyboardButton("🗑️ Delete Link", callback_data=f"delete_file_{file_id}")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Generated link for file {file_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating link: {e}")
        await message.reply_text(f"❌ Error generating link: {str(e)}")

async def parse_post_link(link: str) -> tuple:
    """Parse Telegram post link and extract channel ID and message ID"""
    try:
        # Remove any extra parameters
        link = link.split('?')[0]
        
        # Pattern for private channel: https://t.me/c/1234567890/123
        private_pattern = r"https://t\.me/c/(-?\d+)/(\d+)"
        match = re.match(private_pattern, link)
        if match:
            channel_id = int("-100" + match.group(1))
            message_id = int(match.group(2))
            return channel_id, message_id
        
        # Pattern for public channel: https://t.me/channel_username/123
        public_pattern = r"https://t\.me/([^/]+)/(\d+)"
        match = re.match(public_pattern, link)
        if match:
            username = match.group(1)
            message_id = int(match.group(2))
            return f"@{username}", message_id
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error parsing post link: {e}")
        return None, None

@Client.on_callback_query(filters.regex(r"copy_link_(.+)"))
async def copy_link_callback(client: Client, callback_query):
    """Handle copy link callback"""
    encoded_data = callback_query.data.split("_", 2)[2]
    link = f"https://t.me/{client.username}?start={encoded_data}"
    
    await callback_query.answer(f"📋 Link copied to clipboard!\n\n{link}", show_alert=True)

@Client.on_callback_query(filters.regex(r"delete_file_(.+)"))
async def delete_file_callback(client: Client, callback_query):
    """Handle delete file callback"""
    # Check if user is admin
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can delete files!", show_alert=True)
        return
    
    file_id = callback_query.data.split("_", 2)[2]
    
    try:
        # Delete file from database
        await client.db.delete_file(file_id)
        
        # Update message
        await callback_query.message.edit_text(
            "🗑️ **File Deleted!**\n\n"
            "The file and its link have been permanently deleted from the database.",
            reply_markup=None
        )
        
        await callback_query.answer("✅ File deleted successfully!")
        logger.info(f"File {file_id} deleted by user {callback_query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        await callback_query.answer("❌ Error deleting file!", show_alert=True)

# Alternative command for generating links with reply
@Client.on_message(filters.command("link") & admin_only & filters.reply)
async def link_reply_command(client: Client, message: Message):
    """Generate link by replying to a channel post"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if await client.db.is_user_banned(user_id):
        await message.reply_text("⚠️ You are banned from using this bot!")
        return
    
    replied_message = message.reply_to_message
    
    # Check if the replied message is forwarded from a channel
    if not replied_message.forward_from_chat:
        await message.reply_text("❌ Please reply to a forwarded message from a channel!")
        return
    
    if replied_message.forward_from_chat.type != "channel":
        await message.reply_text("❌ The message must be forwarded from a channel!")
        return
    
    # Check if message has media
    if not (replied_message.document or replied_message.video or replied_message.audio or 
            replied_message.photo or replied_message.animation or replied_message.voice or 
            replied_message.video_note or replied_message.sticker):
        await message.reply_text("❌ The message doesn't contain any media file!")
        return
    
    try:
        channel_id = replied_message.forward_from_chat.id
        message_id = replied_message.forward_from_message_id
        
        # Prepare file data
        file_data = {
            'user_id': user_id,
            'channel_id': channel_id,
            'message_id': message_id,
            'file_name': get_name(replied_message),
            'file_size': get_media_file_size(replied_message),
            'file_type': get_file_type(replied_message),
            'file_hash': get_hash(replied_message),
            'upload_date': replied_message.date.strftime("%Y-%m-%d %H:%M:%S") if replied_message.date else "Unknown"
        }
        
        # Add human readable file size
        file_data['file_size_human'] = get_size(file_data['file_size'])
        
        # Save file to database
        file_id = await client.db.save_file("", file_data)
        
        # Generate shareable link
        encoded_data = encode(file_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Apply URL shortener if enabled
        share_link = await shortener.shorten_url(share_link)
        
        # Create response
        response_text = f"""
✅ **Link Generated Successfully!**

📁 **File Name:** `{file_data['file_name']}`
📊 **File Size:** `{file_data['file_size_human']}`
📂 **File Type:** `{file_data['file_type'].title()}`
📅 **Date:** `{file_data['upload_date']}`

🔗 **Shareable Link:**
`{share_link}`
"""
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open Link", url=share_link)],
            [
                InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_link_{encoded_data}"),
                InlineKeyboardButton("📤 Share", switch_inline_query=share_link)
            ]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Generated link for forwarded file {file_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating link from reply: {e}")
        await message.reply_text(f"❌ Error generating link: {str(e)}")
