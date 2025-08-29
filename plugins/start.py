#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Start command and file handling plugin
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from config import Config
from helper_func import (
    encode, decode, get_name, get_media_file_size, get_hash, 
    get_file_type, is_subscribed, get_start_message
)
from shortener import shortener
import asyncio
import random

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Add user to database
    await client.db.add_user(user_id)
    
    # Check if user is banned
    if await client.db.is_user_banned(user_id):
        await message.reply_text("⚠️ You are banned from using this bot!")
        return
    
    # Check for file/batch access
    if len(message.command) > 1:
        data = message.command[1]
        await handle_file_access(client, message, data)
        return
    
    # Check force subscription
    force_sub_channels = await client.db.get_force_sub_channels()
    if await client.db.is_force_sub_enabled() and force_sub_channels:
        is_subscribed_result, channel = await is_subscribed(client, user_id, force_sub_channels)
        if not is_subscribed_result:
            invite_link = await client.create_chat_invite_link(channel.id)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=invite_link.invite_link)],
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_fsub")]
            ])
            await message.reply_text(
                f"⚠️ You must join our channel to use this bot!\n\n"
                f"📢 Channel: {channel.title}\n"
                f"👆 Click the button above to join and then click refresh.",
                reply_markup=keyboard
            )
            return
    
    # Send start message
    start_msg = get_start_message(first_name, user_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Updates", url="https://t.me/codeflix_bots"),
            InlineKeyboardButton("💬 Support", url="https://t.me/codeflix_bots")
        ],
        [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/codeflix_bots")]
    ])
    
    # Send photo with start message
    try:
        photo_url = random.choice(Config.PICS)
        await message.reply_photo(
            photo=photo_url,
            caption=start_msg,
            reply_markup=keyboard
        )
    except Exception:
        await message.reply_text(start_msg, reply_markup=keyboard)

async def handle_file_access(client: Client, message: Message, data: str):
    """Handle file/batch access from start parameter"""
    user_id = message.from_user.id
    
    try:
        # Decode the data
        decoded_data = decode(data)
        
        if decoded_data.startswith("file_"):
            # Single file access
            file_data = await client.db.get_file(decoded_data)
            if not file_data:
                await message.reply_text("❌ File not found or expired!")
                return
            
            # Send the file
            await send_file_to_user(client, message, file_data)
            
        elif decoded_data.startswith("batch_"):
            # Batch access
            batch_data = await client.db.get_batch(decoded_data)
            if not batch_data:
                await message.reply_text("❌ Batch not found or expired!")
                return
            
            # Send all files in batch
            await send_batch_to_user(client, message, batch_data)
            
        else:
            await message.reply_text("❌ Invalid link!")
            
    except Exception as e:
        logger.error(f"Error handling file access: {e}")
        await message.reply_text("❌ Error processing your request!")

async def send_file_to_user(client: Client, message: Message, file_data: dict):
    """Send a single file to user"""
    try:
        channel_id = file_data['channel_id']
        message_id = file_data['message_id']
        
        # Get the file message from channel
        file_msg = await client.get_messages(channel_id, message_id)
        
        if not file_msg:
            await message.reply_text("❌ File not found in channel!")
            return
        
        # Copy the file to user
        caption = f"📁 **File Name:** `{file_data.get('file_name', 'Unknown')}`\n"
        caption += f"📊 **Size:** `{file_data.get('file_size_human', 'Unknown')}`\n"
        caption += f"📅 **Uploaded:** `{file_data.get('upload_date', 'Unknown')}`\n\n"
        caption += "**Powered by:** @YourBotUsername"
        
        await file_msg.copy(
            chat_id=message.chat.id,
            caption=caption,
            protect_content=Config.PROTECT_CONTENT
        )
        
        # Schedule auto-delete if enabled
        if await client.db.is_auto_delete_enabled():
            auto_delete_time = await client.db.get_auto_delete_time()
            asyncio.create_task(schedule_message_delete(client, message.chat.id, auto_delete_time))
        
    except Exception as e:
        logger.error(f"Error sending file to user: {e}")
        await message.reply_text("❌ Error sending file!")

async def send_batch_to_user(client: Client, message: Message, batch_data: dict):
    """Send batch files to user"""
    try:
        file_ids = batch_data.get('file_ids', [])
        
        if not file_ids:
            await message.reply_text("❌ No files found in this batch!")
            return
        
        await message.reply_text(f"📦 **Batch Files:** {len(file_ids)} files\n\nSending files...")
        
        for i, file_id in enumerate(file_ids, 1):
            file_data = await client.db.get_file(file_id)
            if file_data:
                try:
                    channel_id = file_data['channel_id']
                    message_id = file_data['message_id']
                    
                    file_msg = await client.get_messages(channel_id, message_id)
                    if file_msg:
                        caption = f"📁 **File {i}/{len(file_ids)}**\n"
                        caption += f"**Name:** `{file_data.get('file_name', 'Unknown')}`\n"
                        caption += f"**Size:** `{file_data.get('file_size_human', 'Unknown')}`"
                        
                        await file_msg.copy(
                            chat_id=message.chat.id,
                            caption=caption,
                            protect_content=Config.PROTECT_CONTENT
                        )
                        
                        # Small delay between files
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error sending file {i}: {e}")
                    continue
        
        await message.reply_text("✅ All files sent successfully!")
        
        # Schedule auto-delete if enabled
        if await client.db.is_auto_delete_enabled():
            auto_delete_time = await client.db.get_auto_delete_time()
            asyncio.create_task(schedule_message_delete(client, message.chat.id, auto_delete_time))
        
    except Exception as e:
        logger.error(f"Error sending batch to user: {e}")
        await message.reply_text("❌ Error sending batch files!")

async def schedule_message_delete(client: Client, chat_id: int, delay: int):
    """Schedule message deletion after delay"""
    try:
        await asyncio.sleep(delay)
        # Delete messages (this is a simplified version)
        # In practice, you'd store message IDs and delete them
        logger.info(f"Auto-delete triggered for chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in auto-delete: {e}")

@Client.on_callback_query(filters.regex("refresh_fsub"))
async def refresh_force_sub(client: Client, callback_query: CallbackQuery):
    """Handle force subscription refresh"""
    user_id = callback_query.from_user.id
    
    force_sub_channels = await client.db.get_force_sub_channels()
    if await client.db.is_force_sub_enabled() and force_sub_channels:
        is_subscribed_result, channel = await is_subscribed(client, user_id, force_sub_channels)
        if not is_subscribed_result:
            await callback_query.answer("❌ You still haven't joined the channel!", show_alert=True)
            return
    
    await callback_query.answer("✅ Subscription verified!")
    await callback_query.message.delete()
    
    # Send start message
    first_name = callback_query.from_user.first_name
    start_msg = get_start_message(first_name, user_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Updates", url="https://t.me/codeflix_bots"),
            InlineKeyboardButton("💬 Support", url="https://t.me/codeflix_bots")
        ],
        [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/codeflix_bots")]
    ])
    
    await callback_query.message.reply_text(start_msg, reply_markup=keyboard)

@Client.on_message(filters.private & filters.media & ~filters.command(['start']))
async def handle_private_media(client: Client, message: Message):
    """Handle media files sent to bot"""
    user_id = message.from_user.id
    
    # Check if user is admin or owner
    if not await client.db.is_admin(user_id):
        await message.reply_text(
            "❌ Only admins can upload files!\n\n"
            "Use /genlink command to generate links for existing channel posts."
        )
        return
    
    # Check if user is banned
    if await client.db.is_user_banned(user_id):
        await message.reply_text("⚠️ You are banned from using this bot!")
        return
    
    # Check file size
    file_size = get_media_file_size(message)
    if file_size > Config.MAX_FILE_SIZE:
        await message.reply_text(f"❌ File too large! Maximum size: {Config.MAX_FILE_SIZE / (1024*1024)} MB")
        return
    
    try:
        # Forward file to channel
        forwarded_msg = await message.forward(Config.CHANNEL_ID)
        
        # Save file data
        file_data = {
            'user_id': user_id,
            'channel_id': Config.CHANNEL_ID,
            'message_id': forwarded_msg.id,
            'file_name': get_name(message),
            'file_size': file_size,
            'file_size_human': f"{file_size / (1024*1024):.2f} MB" if file_size > 1024*1024 else f"{file_size / 1024:.2f} KB",
            'file_type': get_file_type(message),
            'file_hash': get_hash(message),
            'upload_date': message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else "Unknown"
        }
        
        file_id = await client.db.save_file("", file_data)
        
        # Generate link
        encoded_data = encode(file_id)
        link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Apply URL shortener if enabled
        link = await shortener.shorten_url(link)
        
        # Send confirmation
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Share Link", url=link)],
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{encoded_data}")]
        ])
        
        await message.reply_text(
            f"✅ **File uploaded successfully!**\n\n"
            f"📁 **Name:** `{file_data['file_name']}`\n"
            f"📊 **Size:** `{file_data['file_size_human']}`\n"
            f"🔗 **Link:** `{link}`\n\n"
            f"👆 Use the buttons above to share the file!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        await message.reply_text("❌ Error uploading file!")

@Client.on_callback_query(filters.regex(r"copy_(.+)"))
async def copy_link_callback(client: Client, callback_query: CallbackQuery):
    """Handle copy link callback"""
    encoded_data = callback_query.data.split("_", 1)[1]
    link = f"https://t.me/{client.username}?start={encoded_data}"
    
    # Apply URL shortener if enabled
    link = await shortener.shorten_url(link)
    
    await callback_query.answer(f"Link copied!\n{link}", show_alert=True)
