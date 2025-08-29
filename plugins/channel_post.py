#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Channel post handler for automatic link generation
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from helper_func import encode, get_name, get_media_file_size, get_file_type, get_hash, get_size
from shortener import shortener

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & filters.media)
async def handle_channel_post(client: Client, message: Message):
    """Handle new posts in the configured channel"""
    
    # Only process posts from the configured channel
    if message.chat.id != Config.CHANNEL_ID:
        return
    
    # Skip if no media
    if not (message.document or message.video or message.audio or 
            message.photo or message.animation or message.voice or 
            message.video_note or message.sticker):
        return
    
    try:
        # Prepare file data
        file_data = {
            'user_id': 0,  # System generated
            'channel_id': message.chat.id,
            'message_id': message.id,
            'file_name': get_name(message),
            'file_size': get_media_file_size(message),
            'file_type': get_file_type(message),
            'file_hash': get_hash(message),
            'auto_generated': True,
            'upload_date': message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else "Unknown"
        }
        
        # Add human readable file size
        file_data['file_size_human'] = get_size(file_data['file_size'])
        
        # Save file to database
        file_id = await client.db.save_file("", file_data)
        
        # Generate shareable link
        encoded_data = encode(file_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        logger.info(f"Auto-generated link for channel post {message.id}: {file_id}")
        
        # Optionally, you can edit the channel post to add the link
        # This is commented out by default to avoid spam
        """
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Get File", url=share_link)]
            ])
            
            await message.edit_reply_markup(keyboard)
        except Exception as e:
            logger.error(f"Error adding button to channel post: {e}")
        """
        
    except Exception as e:
        logger.error(f"Error processing channel post: {e}")

@Client.on_message(filters.channel & filters.text & filters.regex(r"#genlink"))
async def handle_genlink_hashtag(client: Client, message: Message):
    """Handle #genlink hashtag in channel posts"""
    
    # Only process posts from the configured channel
    if message.chat.id != Config.CHANNEL_ID:
        return
    
    # Check if this is a reply to a media message
    if not message.reply_to_message:
        return
    
    replied_msg = message.reply_to_message
    
    # Skip if no media in replied message
    if not (replied_msg.document or replied_msg.video or replied_msg.audio or 
            replied_msg.photo or replied_msg.animation or replied_msg.voice or 
            replied_msg.video_note or replied_msg.sticker):
        return
    
    try:
        # Prepare file data
        file_data = {
            'user_id': 0,  # System generated
            'channel_id': message.chat.id,
            'message_id': replied_msg.id,
            'file_name': get_name(replied_msg),
            'file_size': get_media_file_size(replied_msg),
            'file_type': get_file_type(replied_msg),
            'file_hash': get_hash(replied_msg),
            'auto_generated': True,
            'hashtag_triggered': True,
            'upload_date': replied_msg.date.strftime("%Y-%m-%d %H:%M:%S") if replied_msg.date else "Unknown"
        }
        
        # Add human readable file size
        file_data['file_size_human'] = get_size(file_data['file_size'])
        
        # Save file to database
        file_id = await client.db.save_file("", file_data)
        
        # Generate shareable link
        encoded_data = encode(file_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Create response message
        response_text = f"""
🔗 **Link Generated**

📁 **File:** `{file_data['file_name']}`
📊 **Size:** `{file_data['file_size_human']}`
🔗 **Link:** `{share_link}`
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Get File", url=share_link)]
        ])
        
        # Send response
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Generated link via hashtag for message {replied_msg.id}: {file_id}")
        
    except Exception as e:
        logger.error(f"Error processing hashtag genlink: {e}")

@Client.on_message(filters.group & filters.incoming & filters.regex(r"(?i)(?:generate|create|make|gen)\s+(?:link|url)"))
async def handle_group_genlink_request(client: Client, message: Message):
    """Handle link generation requests in groups"""
    
    # Check if bot is admin in this group
    try:
        bot_member = await client.get_chat_member(message.chat.id, client.id)
        if not bot_member.privileges or not bot_member.privileges.can_delete_messages:
            return
    except:
        return
    
    # Check if this is a reply to a media message
    if not message.reply_to_message:
        await message.reply_text("❌ Please reply to a media message to generate link!")
        return
    
    replied_msg = message.reply_to_message
    
    # Skip if no media in replied message
    if not (replied_msg.document or replied_msg.video or replied_msg.audio or 
            replied_msg.photo or replied_msg.animation or replied_msg.voice or 
            replied_msg.video_note or replied_msg.sticker):
        await message.reply_text("❌ The replied message doesn't contain any media!")
        return
    
    # Check if user is admin
    user_id = message.from_user.id
    if user_id not in Config.ADMINS:
        await message.reply_text("❌ Only admins can generate links!")
        return
    
    try:
        # Forward the media to the storage channel first
        forwarded_msg = await replied_msg.forward(Config.CHANNEL_ID)
        
        # Prepare file data
        file_data = {
            'user_id': user_id,
            'channel_id': Config.CHANNEL_ID,
            'message_id': forwarded_msg.id,
            'file_name': get_name(replied_msg),
            'file_size': get_media_file_size(replied_msg),
            'file_type': get_file_type(replied_msg),
            'file_hash': get_hash(replied_msg),
            'from_group': True,
            'group_id': message.chat.id,
            'upload_date': replied_msg.date.strftime("%Y-%m-%d %H:%M:%S") if replied_msg.date else "Unknown"
        }
        
        # Add human readable file size
        file_data['file_size_human'] = get_size(file_data['file_size'])
        
        # Save file to database
        file_id = await client.db.save_file("", file_data)
        
        # Generate shareable link
        encoded_data = encode(file_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Create response message
        response_text = f"""
✅ **Link Generated Successfully!**

📁 **File:** `{file_data['file_name']}`
📊 **Size:** `{file_data['file_size_human']}`
🔗 **Link:** `{share_link}`

👆 Click the button below to get the file!
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Get File", url=share_link)],
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_link_{encoded_data}")]
        ])
        
        # Send response
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Generated link from group {message.chat.id} for file {file_id}")
        
    except Exception as e:
        logger.error(f"Error generating link from group: {e}")
        await message.reply_text(f"❌ Error generating link: {str(e)}")

@Client.on_message(filters.private & filters.text & filters.regex(r"(?i)(?:generate|create|make|gen)\s+(?:link|url)"))
async def handle_private_genlink_request(client: Client, message: Message):
    """Handle link generation requests in private chats"""
    
    user_id = message.from_user.id
    
    # Check if user is admin
    if user_id not in Config.ADMINS:
        await message.reply_text(
            "❌ Only admins can generate links!\n\n"
            "📝 **Available Commands:**\n"
            "• `/genlink <post_link>` - Generate link for single post\n"
            "• `/batch <channel> <first_id> <last_id>` - Generate batch link\n"
            "• `/start` - Get bot information"
        )
        return
    
    await message.reply_text(
        "📝 **Link Generation Commands:**\n\n"
        "🔗 **Single Link:**\n"
        "`/genlink <channel_post_link>`\n\n"
        "📦 **Batch Link:**\n"
        "`/batch <channel_link> <first_id> <last_id>`\n\n"
        "🎯 **Custom Batch:**\n"
        "`/custom_batch <channel_link> <msg_ids>`\n\n"
        "📤 **Direct Upload:**\n"
        "Send any media file directly to generate link\n\n"
        "📋 **Reply Method:**\n"
        "Forward a channel post and reply with `/link`"
    )
