#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Broadcast plugin for sending messages to all users
"""

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid
from config import Config
from helper_func import send_msg, get_readable_time

logger = logging.getLogger(__name__)

# Admin filter
def admin_filter(_, __, message):
    return message.from_user.id in Config.ADMINS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("broadcast") & admin_only)
async def broadcast_command(client: Client, message: Message):
    """Broadcast message to all users"""
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply_text(
            "❌ **Usage:** Reply to a message with `/broadcast`\n\n"
            "📝 **Note:** The replied message will be sent to all bot users.\n"
            "⚠️ **Warning:** This action cannot be undone!"
        )
        return
    
    # Get confirmation
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_broadcast_{message.reply_to_message.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        ]
    ])
    
    users_count = await client.db.get_users_count()
    
    await message.reply_text(
        f"📢 **Broadcast Confirmation**\n\n"
        f"👥 **Target Users:** `{users_count}`\n"
        f"📝 **Message Preview:** [Click to view](https://t.me/c/{str(message.chat.id)[4:]}/{message.reply_to_message.id})\n\n"
        f"⚠️ Are you sure you want to broadcast this message?",
        reply_markup=keyboard
    )

@Client.on_message(filters.command("dbroadcast") & admin_only)
async def delayed_broadcast_command(client: Client, message: Message):
    """Broadcast message with auto-delete"""
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply_text(
            "❌ **Usage:** Reply to a message with `/dbroadcast`\n\n"
            "📝 **Note:** The message will be sent to all users and auto-deleted after the configured time.\n"
            "⚠️ **Warning:** This action cannot be undone!"
        )
        return
    
    # Get auto-delete time
    delete_time = await client.db.get_auto_delete_time()
    readable_time = get_readable_time(delete_time)
    
    # Get confirmation
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_dbroadcast_{message.reply_to_message.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        ]
    ])
    
    users_count = await client.db.get_users_count()
    
    await message.reply_text(
        f"📢 **Auto-Delete Broadcast Confirmation**\n\n"
        f"👥 **Target Users:** `{users_count}`\n"
        f"🗑️ **Auto-Delete Time:** `{readable_time}`\n"
        f"📝 **Message Preview:** [Click to view](https://t.me/c/{str(message.chat.id)[4:]}/{message.reply_to_message.id})\n\n"
        f"⚠️ Are you sure you want to broadcast this message?",
        reply_markup=keyboard
    )

@Client.on_message(filters.command("pbroadcast") & admin_only)
async def pin_broadcast_command(client: Client, message: Message):
    """Pin broadcast message to all users"""
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        await message.reply_text(
            "❌ **Usage:** Reply to a message with `/pbroadcast`\n\n"
            "📝 **Note:** The message will be sent and pinned to all users' private chats.\n"
            "⚠️ **Warning:** This action cannot be undone!"
        )
        return
    
    # Get confirmation
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_pbroadcast_{message.reply_to_message.id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        ]
    ])
    
    users_count = await client.db.get_users_count()
    
    await message.reply_text(
        f"📌 **Pin Broadcast Confirmation**\n\n"
        f"👥 **Target Users:** `{users_count}`\n"
        f"📝 **Message Preview:** [Click to view](https://t.me/c/{str(message.chat.id)[4:]}/{message.reply_to_message.id})\n\n"
        f"⚠️ Are you sure you want to pin broadcast this message?",
        reply_markup=keyboard
    )

# Callback handlers
@Client.on_callback_query(filters.regex(r"confirm_broadcast_(\d+)"))
async def confirm_broadcast_callback(client: Client, callback_query):
    """Handle broadcast confirmation"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    message_id = int(callback_query.data.split("_")[2])
    
    try:
        # Get the message to broadcast
        broadcast_msg = await client.get_messages(callback_query.message.chat.id, message_id)
        if not broadcast_msg:
            await callback_query.answer("❌ Message not found!", show_alert=True)
            return
        
        # Start broadcasting
        await callback_query.answer("✅ Broadcasting started!")
        await start_broadcast(client, callback_query.message, broadcast_msg, "normal")
        
    except Exception as e:
        logger.error(f"Error in broadcast confirmation: {e}")
        await callback_query.answer("❌ Error starting broadcast!", show_alert=True)

@Client.on_callback_query(filters.regex(r"confirm_dbroadcast_(\d+)"))
async def confirm_dbroadcast_callback(client: Client, callback_query):
    """Handle delayed broadcast confirmation"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    message_id = int(callback_query.data.split("_")[2])
    
    try:
        # Get the message to broadcast
        broadcast_msg = await client.get_messages(callback_query.message.chat.id, message_id)
        if not broadcast_msg:
            await callback_query.answer("❌ Message not found!", show_alert=True)
            return
        
        # Start broadcasting
        await callback_query.answer("✅ Auto-delete broadcasting started!")
        await start_broadcast(client, callback_query.message, broadcast_msg, "auto_delete")
        
    except Exception as e:
        logger.error(f"Error in dbroadcast confirmation: {e}")
        await callback_query.answer("❌ Error starting broadcast!", show_alert=True)

@Client.on_callback_query(filters.regex(r"confirm_pbroadcast_(\d+)"))
async def confirm_pbroadcast_callback(client: Client, callback_query):
    """Handle pin broadcast confirmation"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    message_id = int(callback_query.data.split("_")[2])
    
    try:
        # Get the message to broadcast
        broadcast_msg = await client.get_messages(callback_query.message.chat.id, message_id)
        if not broadcast_msg:
            await callback_query.answer("❌ Message not found!", show_alert=True)
            return
        
        # Start broadcasting
        await callback_query.answer("✅ Pin broadcasting started!")
        await start_broadcast(client, callback_query.message, broadcast_msg, "pin")
        
    except Exception as e:
        logger.error(f"Error in pbroadcast confirmation: {e}")
        await callback_query.answer("❌ Error starting broadcast!", show_alert=True)

@Client.on_callback_query(filters.regex("cancel_broadcast"))
async def cancel_broadcast_callback(client: Client, callback_query):
    """Handle broadcast cancellation"""
    await callback_query.answer("❌ Broadcast cancelled!")
    await callback_query.message.edit_text(
        "❌ **Broadcast Cancelled**\n\n"
        "The broadcast operation has been cancelled.",
        reply_markup=None
    )

async def start_broadcast(client: Client, status_message: Message, broadcast_msg: Message, broadcast_type: str):
    """Start the broadcasting process"""
    
    # Get all users
    all_users = await client.db.get_all_users()
    banned_users = await client.db.get_banned_users()
    
    # Filter out banned users
    target_users = [user for user in all_users if user not in banned_users]
    
    total_users = len(target_users)
    success_count = 0
    failed_count = 0
    blocked_count = 0
    deleted_count = 0
    
    # Update status message
    await status_message.edit_text(
        f"📢 **Broadcasting in Progress...**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"✅ **Sent:** `0`\n"
        f"❌ **Failed:** `0`\n"
        f"🚫 **Blocked:** `0`\n"
        f"👻 **Deleted:** `0`\n\n"
        f"⏳ **Progress:** `0%`"
    )
    
    # Track messages for auto-delete
    sent_messages = []
    
    # Start broadcasting
    for i, user_id in enumerate(target_users):
        try:
            if broadcast_type == "pin":
                # Send and pin the message
                sent_msg = await broadcast_msg.copy(user_id)
                try:
                    await client.pin_chat_message(user_id, sent_msg.id, disable_notification=True)
                except:
                    pass  # Ignore pin errors
            else:
                # Regular send
                sent_msg = await broadcast_msg.copy(user_id)
            
            success_count += 1
            
            # Store message for auto-delete
            if broadcast_type == "auto_delete":
                sent_messages.append((user_id, sent_msg.id))
            
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent_msg = await broadcast_msg.copy(user_id)
                success_count += 1
                
                if broadcast_type == "auto_delete":
                    sent_messages.append((user_id, sent_msg.id))
                    
            except Exception:
                failed_count += 1
                
        except UserIsBlocked:
            blocked_count += 1
            
        except InputUserDeactivated:
            deleted_count += 1
            
        except PeerIdInvalid:
            deleted_count += 1
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Error broadcasting to {user_id}: {e}")
        
        # Update progress every 50 users or at the end
        if (i + 1) % 50 == 0 or i == total_users - 1:
            progress = ((i + 1) / total_users) * 100
            
            try:
                await status_message.edit_text(
                    f"📢 **Broadcasting in Progress...**\n\n"
                    f"👥 **Total Users:** `{total_users}`\n"
                    f"✅ **Sent:** `{success_count}`\n"
                    f"❌ **Failed:** `{failed_count}`\n"
                    f"🚫 **Blocked:** `{blocked_count}`\n"
                    f"👻 **Deleted:** `{deleted_count}`\n\n"
                    f"⏳ **Progress:** `{progress:.1f}%`"
                )
            except:
                pass
        
        # Small delay to avoid flooding
        await asyncio.sleep(0.1)
    
    # Final status update
    broadcast_type_name = {
        "normal": "Broadcast",
        "auto_delete": "Auto-Delete Broadcast", 
        "pin": "Pin Broadcast"
    }.get(broadcast_type, "Broadcast")
    
    final_text = f"""
✅ **{broadcast_type_name} Completed!**

📊 **Results:**
👥 **Total Users:** `{total_users}`
✅ **Successfully Sent:** `{success_count}`
❌ **Failed:** `{failed_count}`
🚫 **Blocked Bot:** `{blocked_count}`
👻 **Deleted Account:** `{deleted_count}`

📈 **Success Rate:** `{(success_count/total_users*100) if total_users > 0 else 0:.1f}%`
"""
    
    if broadcast_type == "auto_delete":
        delete_time = await client.db.get_auto_delete_time()
        readable_time = get_readable_time(delete_time)
        final_text += f"\n🗑️ **Auto-Delete:** Messages will be deleted in `{readable_time}`"
    
    await status_message.edit_text(final_text)
    
    # Schedule auto-delete if needed
    if broadcast_type == "auto_delete" and sent_messages:
        asyncio.create_task(schedule_broadcast_delete(client, sent_messages))
    
    logger.info(f"Broadcast completed: {success_count}/{total_users} sent successfully")

async def schedule_broadcast_delete(client: Client, sent_messages: list):
    """Schedule deletion of broadcast messages"""
    try:
        delete_time = await client.db.get_auto_delete_time()
        await asyncio.sleep(delete_time)
        
        deleted_count = 0
        
        for user_id, message_id in sent_messages:
            try:
                await client.delete_messages(user_id, message_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting broadcast message for {user_id}: {e}")
            
            # Small delay
            await asyncio.sleep(0.1)
        
        logger.info(f"Auto-deleted {deleted_count}/{len(sent_messages)} broadcast messages")
        
    except Exception as e:
        logger.error(f"Error in broadcast auto-delete: {e}")
