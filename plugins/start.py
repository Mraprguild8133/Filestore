#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Start command and file handling plugin
"""

import logging
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from config import Config
from helper_func import (
    encode, decode, get_name, get_media_file_size, get_hash, 
    get_file_type, is_subscribed, get_start_message, get_messages,
    get_exp_time, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT,
    START_PIC, START_MSG, FORCE_PIC, FORCE_MSG, CMD_TXT, FSUB_LINK_EXPIRY,
    BAN_SUPPORT
)
from shortener import shortener
from database.database import db

logger = logging.getLogger(__name__)

# Create a global dictionary to store chat data
chat_data_cache = {}

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Add user to database if not present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
    
    # Check if user is banned
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        await message.reply_text(
            "<b>⛔️ You are Banned from using this bot.</b>\n\n"
            "<i>Contact support if you think this is a mistake.</i>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]]
            )
        )
        return
    
    # Check force subscription
    if not await is_subscribed(client, user_id):
        await not_joined(client, message)
        return
    
    # Handle file/batch access if parameter provided
    if len(message.command) > 1:
        data = message.command[1]
        await handle_file_access(client, message, data)
        return
    
    # Send start message
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("• ᴍᴏʀᴇ ᴄʜᴀɴɴᴇʟs •", url="https://t.me/Nova_Flix/50")],
        [
            InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
            InlineKeyboardButton("ʜᴇʟᴘ •", callback_data="help")
        ]
    ])
    
    # Send photo with start message
    try:
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            message_effect_id=5104841245755180586  # 🔥
        )
    except Exception as e:
        logger.error(f"Error sending start message: {e}")
        await message.reply_text(
            START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup
        )

async def handle_file_access(client: Client, message: Message, data: str):
    """Handle file/batch access from start parameter"""
    user_id = message.from_user.id
    
    try:
        # Decode the data
        decoded_data = decode(data)
        
        if decoded_data.startswith("file_"):
            # Single file access
            file_data = await db.get_file(decoded_data)
            if not file_data:
                await message.reply_text("❌ File not found or expired!")
                return
            
            # Send the file
            await send_file_to_user(client, message, file_data)
            
        elif decoded_data.startswith("batch_"):
            # Batch access
            batch_data = await db.get_batch(decoded_data)
            if not batch_data:
                await message.reply_text("❌ Batch not found or expired!")
                return
            
            # Send all files in batch
            await send_batch_to_user(client, message, batch_data)
            
        else:
            # Handle legacy format
            await handle_legacy_format(client, message, decoded_data)
            
    except Exception as e:
        logger.error(f"Error handling file access: {e}")
        await message.reply_text("❌ Error processing your request!")

async def handle_legacy_format(client: Client, message: Message, string: str):
    """Handle legacy format for backward compatibility"""
    argument = string.split("-")
    ids = []
    
    if len(argument) == 3:
        try:
            start = int(int(argument[1]) / abs(client.db_channel.id))
            end = int(int(argument[2]) / abs(client.db_channel.id))
            ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
        except Exception as e:
            logger.error(f"Error decoding IDs: {e}")
            return

    elif len(argument) == 2:
        try:
            ids = [int(int(argument[1]) / abs(client.db_channel.id))]
        except Exception as e:
            logger.error(f"Error decoding ID: {e}")
            return

    temp_msg = await message.reply("<b>Please wait...</b>")
    try:
        messages = await get_messages(client, ids)
    except Exception as e:
        await message.reply_text("Something went wrong!")
        logger.error(f"Error getting messages: {e}")
        return
    finally:
        await temp_msg.delete()

    codeflix_msgs = []
    for msg in messages:
        caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, 
                                         filename=msg.document.file_name) if bool(CUSTOM_CAPTION) and bool(msg.document)
                   else ("" if not msg.caption else msg.caption.html))
        reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None
        try:
            copied_msg = await msg.copy(
                chat_id=message.from_user.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_CONTENT
            )
            await asyncio.sleep(0.1)
            codeflix_msgs.append(copied_msg)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    # Schedule auto-delete if enabled
    FILE_AUTO_DELETE = await db.get_del_timer()
    if FILE_AUTO_DELETE > 0:
        notification_msg = await message.reply(
            f"<b>This file will be deleted in {get_exp_time(FILE_AUTO_DELETE)}. Please save or forward it to your saved messages before it gets deleted.</b>"
        )
        reload_url = f"https://t.me/{client.username}?start={message.command[1]}"
        asyncio.create_task(
            schedule_auto_delete(client, codeflix_msgs, notification_msg, FILE_AUTO_DELETE, reload_url)
        )

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
            protect_content=PROTECT_CONTENT
        )
        
        # Schedule auto-delete if enabled
        FILE_AUTO_DELETE = await db.get_del_timer()
        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>This file will be deleted in {get_exp_time(FILE_AUTO_DELETE)}. Please save or forward it to your saved messages before it gets deleted.</b>"
            )
            reload_url = f"https://t.me/{client.username}?start={message.command[1]}"
            asyncio.create_task(
                schedule_auto_delete(client, [file_msg], notification_msg, FILE_AUTO_DELETE, reload_url)
            )
        
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
        
        codeflix_msgs = []
        for i, file_id in enumerate(file_ids, 1):
            file_data = await db.get_file(file_id)
            if file_data:
                try:
                    channel_id = file_data['channel_id']
                    message_id = file_data['message_id']
                    
                    file_msg = await client.get_messages(channel_id, message_id)
                    if file_msg:
                        caption = f"📁 **File {i}/{len(file_ids)}**\n"
                        caption += f"**Name:** `{file_data.get('file_name', 'Unknown')}`\n"
                        caption += f"**Size:** `{file_data.get('file_size_human', 'Unknown')}`"
                        
                        copied_msg = await file_msg.copy(
                            chat_id=message.chat.id,
                            caption=caption,
                            protect_content=PROTECT_CONTENT
                        )
                        codeflix_msgs.append(copied_msg)
                        
                        # Small delay between files
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error sending file {i}: {e}")
                    continue
        
        await message.reply_text("✅ All files sent successfully!")
        
        # Schedule auto-delete if enabled
        FILE_AUTO_DELETE = await db.get_del_timer()
        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>These files will be deleted in {get_exp_time(FILE_AUTO_DELETE)}. Please save or forward them to your saved messages before they get deleted.</b>"
            )
            reload_url = f"https://t.me/{client.username}?start={message.command[1]}"
            asyncio.create_task(
                schedule_auto_delete(client, codeflix_msgs, notification_msg, FILE_AUTO_DELETE, reload_url)
            )
        
    except Exception as e:
        logger.error(f"Error sending batch to user: {e}")
        await message.reply_text("❌ Error sending batch files!")

async def schedule_auto_delete(client, messages, notification_msg, delay, reload_url):
    """Schedule message deletion after delay"""
    try:
        await asyncio.sleep(delay)
        
        # Delete all messages
        delete_tasks = []
        for msg in messages:
            if msg:
                delete_tasks.append(msg.delete())
        
        if delete_tasks:
            await asyncio.gather(*delete_tasks, return_exceptions=True)
        
        # Update notification with retry option if URL provided
        if reload_url:
            try:
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                )
                await notification_msg.edit(
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error updating notification: {e}")
        
    except Exception as e:
        logger.error(f"Error in auto-delete: {e}")

async def not_joined(client: Client, message: Message):
    """Handle force subscription requirement"""
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>")

    user_id = message.from_user.id
    buttons = []
    count = 0

    try:
        all_channels = await db.show_channels()  # Should return list of (chat_id, mode) tuples
        for chat_id in all_channels:
            mode = await db.get_channel_mode(chat_id)  # fetch mode 

            await message.reply_chat_action(ChatAction.TYPING)

            if not await is_subscribed(client, user_id, chat_id):
                try:
                    # Cache chat info
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data

                    name = data.title

                    # Generate proper invite link based on the mode
                    if mode == "on" and not data.username:
                        invite = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                            )
                        link = invite.invite_link

                    else:
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else:
                            invite = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None)
                            link = invite.invite_link

                    buttons.append([InlineKeyboardButton(text=name, url=link)])
                    count += 1
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    logger.error(f"Error with chat {chat_id}: {e}")
                    return await temp.edit(
                        f"<b><i>! Error, Contact developer to solve the issues</i></b>\n"
                        f"<blockquote expandable><b>Reason:</b> {e}</blockquote>"
                    )

        # Retry Button
        try:
            buttons.append([
                InlineKeyboardButton(
                    text='♻️ Try Again',
                    url=f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ])
        except IndexError:
            pass

        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Final Error: {e}")
        await temp.edit(
            f"<b><i>! Error, Contact developer to solve the issues</i></b>\n"
            f"<blockquote expandable><b>Reason:</b> {e}</blockquote>"
        )

@Client.on_callback_query(filters.regex("refresh_fsub"))
async def refresh_force_sub(client: Client, callback_query: CallbackQuery):
    """Handle force subscription refresh"""
    user_id = callback_query.from_user.id
    
    if not await is_subscribed(client, user_id):
        await callback_query.answer("❌ You still haven't joined the channel!", show_alert=True)
        return
    
    await callback_query.answer("✅ Subscription verified!")
    await callback_query.message.delete()
    
    # Resend the start command
    await start_command(client, callback_query.message)

@Client.on_message(filters.command('commands') & filters.private)
async def commands_handler(client: Client, message: Message):        
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data="close")]])
    await message.reply(text=CMD_TXT, reply_markup=reply_markup, quote=True)

@Client.on_message(filters.private & filters.media & ~filters.command(['start']))
async def handle_private_media(client: Client, message: Message):
    """Handle media files sent to bot"""
    user_id = message.from_user.id
    
    # Check if user is admin or owner
    if not await db.is_admin(user_id):
        await message.reply_text(
            "❌ Only admins can upload files!\n\n"
            "Use /genlink command to generate links for existing channel posts."
        )
        return
    
    # Check if user is banned
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
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
        
        file_id = await db.save_file("", file_data)
        
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
