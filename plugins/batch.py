#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch link generation plugin
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from helper_func import encode, get_name, get_media_file_size, get_file_type, get_hash, get_size
from shortener import shortener
import re
import asyncio

logger = logging.getLogger(__name__)

# Admin filter
def admin_filter(_, __, message):
    return message.from_user.id in Config.ADMINS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("batch") & admin_only)
async def batch_command(client: Client, message: Message):
    """Generate batch link for multiple posts"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if await client.db.is_user_banned(user_id):
        await message.reply_text("⚠️ You are banned from using this bot!")
        return
    
    if len(message.command) < 4:
        await message.reply_text(
            "❌ **Usage:** `/batch <channel_link> <first_message_id> <last_message_id>`\n\n"
            "**Example:**\n"
            "`/batch https://t.me/c/1234567890 100 150`\n"
            "`/batch https://t.me/channel_username 100 150`\n\n"
            "📝 **Note:** Make sure I'm added as admin in the channel!"
        )
        return
    
    channel_link = message.command[1]
    
    try:
        first_msg_id = int(message.command[2])
        last_msg_id = int(message.command[3])
    except ValueError:
        await message.reply_text("❌ Invalid message IDs! Please provide valid numbers.")
        return
    
    if first_msg_id >= last_msg_id:
        await message.reply_text("❌ First message ID must be smaller than last message ID!")
        return
    
    if last_msg_id - first_msg_id > 200:
        await message.reply_text("❌ Maximum 200 messages allowed in a batch!")
        return
    
    try:
        # Parse channel ID
        channel_id = await parse_channel_link(channel_link)
        if not channel_id:
            await message.reply_text("❌ Invalid channel link format!")
            return
        
        # Send processing message
        process_msg = await message.reply_text("🔄 Processing batch... Please wait!")
        
        # Process messages
        file_ids = []
        processed = 0
        skipped = 0
        errors = 0
        
        for msg_id in range(first_msg_id, last_msg_id + 1):
            try:
                # Get message from channel
                channel_msg = await client.get_messages(channel_id, msg_id)
                
                if not channel_msg:
                    skipped += 1
                    continue
                
                # Check if message has media
                if not (channel_msg.document or channel_msg.video or channel_msg.audio or 
                        channel_msg.photo or channel_msg.animation or channel_msg.voice or 
                        channel_msg.video_note or channel_msg.sticker):
                    skipped += 1
                    continue
                
                # Prepare file data
                file_data = {
                    'user_id': user_id,
                    'channel_id': channel_id,
                    'message_id': msg_id,
                    'file_name': get_name(channel_msg),
                    'file_size': get_media_file_size(channel_msg),
                    'file_type': get_file_type(channel_msg),
                    'file_hash': get_hash(channel_msg),
                    'upload_date': channel_msg.date.strftime("%Y-%m-%d %H:%M:%S") if channel_msg.date else "Unknown"
                }
                
                # Add human readable file size
                file_data['file_size_human'] = get_size(file_data['file_size'])
                
                # Save file to database
                file_id = await client.db.save_file("", file_data)
                file_ids.append(file_id)
                
                processed += 1
                
                # Update progress every 10 files
                if processed % 10 == 0:
                    await process_msg.edit_text(
                        f"🔄 Processing batch...\n"
                        f"✅ Processed: {processed}\n"
                        f"⏭️ Skipped: {skipped}\n"
                        f"❌ Errors: {errors}"
                    )
                
                # Small delay to avoid flood
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                errors += 1
                continue
        
        if not file_ids:
            await process_msg.edit_text("❌ No valid media files found in the specified range!")
            return
        
        # Create batch data
        batch_data = {
            'user_id': user_id,
            'channel_id': channel_id,
            'file_ids': file_ids,
            'first_message_id': first_msg_id,
            'last_message_id': last_msg_id,
            'total_files': len(file_ids),
            'channel_link': channel_link
        }
        
        # Save batch to database
        batch_id = await client.db.save_batch("", batch_data)
        
        # Generate shareable link
        encoded_data = encode(batch_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Create response
        response_text = f"""
✅ **Batch Created Successfully!**

📦 **Total Files:** `{len(file_ids)}`
✅ **Processed:** `{processed}`
⏭️ **Skipped:** `{skipped}`
❌ **Errors:** `{errors}`

📊 **Range:** `{first_msg_id}` to `{last_msg_id}`
📁 **Channel:** `{channel_id}`

🔗 **Batch Link:**
`{share_link}`

📋 **Quick Copy:**
{share_link}
"""
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open Batch", url=share_link)],
            [
                InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_batch_{encoded_data}"),
                InlineKeyboardButton("📤 Share", switch_inline_query=share_link)
            ],
            [InlineKeyboardButton("🗑️ Delete Batch", callback_data=f"delete_batch_{batch_id}")]
        ])
        
        await process_msg.edit_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Created batch {batch_id} with {len(file_ids)} files by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error creating batch: {e}")
        await message.reply_text(f"❌ Error creating batch: {str(e)}")

@Client.on_message(filters.command("custom_batch") & admin_only)
async def custom_batch_command(client: Client, message: Message):
    """Generate custom batch from selected message IDs"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if await client.db.is_user_banned(user_id):
        await message.reply_text("⚠️ You are banned from using this bot!")
        return
    
    if len(message.command) < 3:
        await message.reply_text(
            "❌ **Usage:** `/custom_batch <channel_link> <message_ids>`\n\n"
            "**Example:**\n"
            "`/custom_batch https://t.me/c/1234567890 100 105 110 115 120`\n"
            "`/custom_batch https://t.me/channel_username 100,105,110,115,120`\n\n"
            "📝 **Note:** You can separate message IDs with spaces or commas\n"
            "📝 **Maximum 100 messages allowed**"
        )
        return
    
    channel_link = message.command[1]
    
    # Parse message IDs
    message_ids_str = " ".join(message.command[2:])
    message_ids_str = message_ids_str.replace(",", " ")
    
    try:
        message_ids = [int(mid.strip()) for mid in message_ids_str.split() if mid.strip()]
    except ValueError:
        await message.reply_text("❌ Invalid message IDs! Please provide valid numbers.")
        return
    
    if not message_ids:
        await message.reply_text("❌ No valid message IDs provided!")
        return
    
    if len(message_ids) > 100:
        await message.reply_text("❌ Maximum 100 messages allowed in a custom batch!")
        return
    
    # Remove duplicates and sort
    message_ids = sorted(list(set(message_ids)))
    
    try:
        # Parse channel ID
        channel_id = await parse_channel_link(channel_link)
        if not channel_id:
            await message.reply_text("❌ Invalid channel link format!")
            return
        
        # Send processing message
        process_msg = await message.reply_text(f"🔄 Processing custom batch with {len(message_ids)} messages... Please wait!")
        
        # Process messages
        file_ids = []
        processed = 0
        skipped = 0
        errors = 0
        
        for i, msg_id in enumerate(message_ids):
            try:
                # Get message from channel
                channel_msg = await client.get_messages(channel_id, msg_id)
                
                if not channel_msg:
                    skipped += 1
                    continue
                
                # Check if message has media
                if not (channel_msg.document or channel_msg.video or channel_msg.audio or 
                        channel_msg.photo or channel_msg.animation or channel_msg.voice or 
                        channel_msg.video_note or channel_msg.sticker):
                    skipped += 1
                    continue
                
                # Prepare file data
                file_data = {
                    'user_id': user_id,
                    'channel_id': channel_id,
                    'message_id': msg_id,
                    'file_name': get_name(channel_msg),
                    'file_size': get_media_file_size(channel_msg),
                    'file_type': get_file_type(channel_msg),
                    'file_hash': get_hash(channel_msg),
                    'upload_date': channel_msg.date.strftime("%Y-%m-%d %H:%M:%S") if channel_msg.date else "Unknown"
                }
                
                # Add human readable file size
                file_data['file_size_human'] = get_size(file_data['file_size'])
                
                # Save file to database
                file_id = await client.db.save_file("", file_data)
                file_ids.append(file_id)
                
                processed += 1
                
                # Update progress every 10 files
                if processed % 10 == 0:
                    await process_msg.edit_text(
                        f"🔄 Processing custom batch... ({i+1}/{len(message_ids)})\n"
                        f"✅ Processed: {processed}\n"
                        f"⏭️ Skipped: {skipped}\n"
                        f"❌ Errors: {errors}"
                    )
                
                # Small delay to avoid flood
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                errors += 1
                continue
        
        if not file_ids:
            await process_msg.edit_text("❌ No valid media files found in the specified messages!")
            return
        
        # Create batch data
        batch_data = {
            'user_id': user_id,
            'channel_id': channel_id,
            'file_ids': file_ids,
            'message_ids': message_ids,
            'total_files': len(file_ids),
            'channel_link': channel_link,
            'batch_type': 'custom'
        }
        
        # Save batch to database
        batch_id = await client.db.save_batch("", batch_data)
        
        # Generate shareable link
        encoded_data = encode(batch_id)
        share_link = f"https://t.me/{client.username}?start={encoded_data}"
        
        # Create response
        response_text = f"""
✅ **Custom Batch Created Successfully!**

📦 **Total Files:** `{len(file_ids)}`
✅ **Processed:** `{processed}`
⏭️ **Skipped:** `{skipped}`
❌ **Errors:** `{errors}`

📊 **Selected Messages:** `{len(message_ids)}`
📁 **Channel:** `{channel_id}`

🔗 **Batch Link:**
`{share_link}`

📋 **Quick Copy:**
{share_link}
"""
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open Batch", url=share_link)],
            [
                InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_batch_{encoded_data}"),
                InlineKeyboardButton("📤 Share", switch_inline_query=share_link)
            ],
            [InlineKeyboardButton("🗑️ Delete Batch", callback_data=f"delete_batch_{batch_id}")]
        ])
        
        await process_msg.edit_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Created custom batch {batch_id} with {len(file_ids)} files by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error creating custom batch: {e}")
        await message.reply_text(f"❌ Error creating custom batch: {str(e)}")

async def parse_channel_link(link: str) -> str:
    """Parse channel link and return channel ID"""
    try:
        # Remove any extra parameters
        link = link.split('?')[0].rstrip('/')
        
        # Pattern for private channel: https://t.me/c/1234567890
        private_pattern = r"https://t\.me/c/(-?\d+)"
        match = re.match(private_pattern, link)
        if match:
            return int("-100" + match.group(1))
        
        # Pattern for public channel: https://t.me/channel_username
        public_pattern = r"https://t\.me/([^/]+)"
        match = re.match(public_pattern, link)
        if match:
            return f"@{match.group(1)}"
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing channel link: {e}")
        return None

@Client.on_callback_query(filters.regex(r"copy_batch_(.+)"))
async def copy_batch_callback(client: Client, callback_query):
    """Handle copy batch link callback"""
    encoded_data = callback_query.data.split("_", 2)[2]
    link = f"https://t.me/{client.username}?start={encoded_data}"
    
    await callback_query.answer(f"📋 Batch link copied to clipboard!\n\n{link}", show_alert=True)

@Client.on_callback_query(filters.regex(r"delete_batch_(.+)"))
async def delete_batch_callback(client: Client, callback_query):
    """Handle delete batch callback"""
    # Check if user is admin
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can delete batches!", show_alert=True)
        return
    
    batch_id = callback_query.data.split("_", 2)[2]
    
    try:
        # Delete batch from database
        await client.db.delete_batch(batch_id)
        
        # Update message
        await callback_query.message.edit_text(
            "🗑️ **Batch Deleted!**\n\n"
            "The batch and its link have been permanently deleted from the database.",
            reply_markup=None
        )
        
        await callback_query.answer("✅ Batch deleted successfully!")
        logger.info(f"Batch {batch_id} deleted by user {callback_query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error deleting batch: {e}")
        await callback_query.answer("❌ Error deleting batch!", show_alert=True)
