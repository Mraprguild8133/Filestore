#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin commands plugin
"""

import logging
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from helper_func import get_readable_time, get_size

logger = logging.getLogger(__name__)

# Admin filter
def admin_filter(_, __, message):
    return message.from_user.id in Config.ADMINS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("stats") & admin_only)
async def stats_command(client: Client, message: Message):
    """Get bot statistics"""
    try:
        stats = await client.db.get_stats()
        
        uptime = get_readable_time(int(stats['uptime']))
        
        stats_text = f"""
📊 **Bot Statistics**

👥 **Users:** `{stats['total_users']}`
🚫 **Banned:** `{stats['total_banned']}`
👮‍♂️ **Admins:** `{stats['total_admins']}`

📁 **Files:** `{stats['current_files']}`
📦 **Batches:** `{stats['current_batches']}`
📤 **Total Uploaded:** `{stats['total_files']}`

⏰ **Uptime:** `{uptime}`
🔗 **Force Sub Channels:** `{stats['force_sub_channels']}`
🗑️ **Auto Delete:** `{'✅ Enabled' if stats['auto_delete_enabled'] else '❌ Disabled'}`
⏱️ **Delete Time:** `{get_readable_time(stats['auto_delete_time'])}`
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")]
        ])
        
        await message.reply_text(stats_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.reply_text("❌ Error getting statistics!")

@Client.on_message(filters.command("users") & admin_only)
async def users_command(client: Client, message: Message):
    """Get users information"""
    try:
        all_users = await client.db.get_all_users()
        banned_users = await client.db.get_banned_users()
        
        total_users = len(all_users)
        total_banned = len(banned_users)
        active_users = total_users - total_banned
        
        text = f"""
👥 **Users Information**

📊 **Total Users:** `{total_users}`
✅ **Active Users:** `{active_users}`
🚫 **Banned Users:** `{total_banned}`

📈 **User Growth:** +{total_users} users
📅 **Last Updated:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 User List", callback_data="user_list"),
                InlineKeyboardButton("🚫 Banned List", callback_data="banned_list")
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_users")]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting users info: {e}")
        await message.reply_text("❌ Error getting users information!")

@Client.on_message(filters.command(["ban", "unban"]) & admin_only)
async def ban_unban_user(client: Client, message: Message):
    """Ban or unban a user"""
    cmd = message.command[0]
    
    if len(message.command) < 2:
        await message.reply_text(f"❌ Usage: `/{cmd} <user_id>`")
        return
    
    try:
        user_id = int(message.command[1])
        
        if cmd == "ban":
            if user_id in Config.ADMINS:
                await message.reply_text("❌ Cannot ban an admin!")
                return
            
            await client.db.ban_user(user_id)
            await message.reply_text(f"✅ User `{user_id}` has been banned!")
            
            # Try to send notification to user
            try:
                await client.send_message(user_id, "⚠️ You have been banned from using this bot!")
            except:
                pass
        
        else:  # unban
            await client.db.unban_user(user_id)
            await message.reply_text(f"✅ User `{user_id}` has been unbanned!")
            
            # Try to send notification to user
            try:
                await client.send_message(user_id, "✅ You have been unbanned! You can now use the bot again.")
            except:
                pass
    
    except ValueError:
        await message.reply_text("❌ Invalid user ID!")
    except Exception as e:
        logger.error(f"Error in ban/unban: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("banlist") & admin_only)
async def banlist_command(client: Client, message: Message):
    """Get list of banned users"""
    try:
        banned_users = await client.db.get_banned_users()
        
        if not banned_users:
            await message.reply_text("✅ No users are currently banned!")
            return
        
        text = "🚫 **Banned Users:**\n\n"
        for i, user_id in enumerate(banned_users[:20], 1):  # Show max 20
            text += f"`{i}.` `{user_id}`\n"
        
        if len(banned_users) > 20:
            text += f"\n... and {len(banned_users) - 20} more users"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_banlist")]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting banlist: {e}")
        await message.reply_text("❌ Error getting banned users list!")

@Client.on_message(filters.command(["add_admin", "deladmin"]) & filters.user(Config.OWNER_ID))
async def manage_admins(client: Client, message: Message):
    """Add or remove admins (owner only)"""
    cmd = message.command[0]
    
    if len(message.command) < 2:
        await message.reply_text(f"❌ Usage: `/{cmd} <user_id>`")
        return
    
    try:
        user_id = int(message.command[1])
        
        if cmd == "add_admin":
            if user_id == Config.OWNER_ID:
                await message.reply_text("❌ Owner is already an admin!")
                return
            
            await client.db.add_admin(user_id)
            await message.reply_text(f"✅ User `{user_id}` has been added as admin!")
            
            # Try to send notification
            try:
                await client.send_message(user_id, "🎉 You have been promoted to admin!")
            except:
                pass
        
        else:  # deladmin
            if user_id == Config.OWNER_ID:
                await message.reply_text("❌ Cannot remove owner from admins!")
                return
            
            await client.db.remove_admin(user_id)
            await message.reply_text(f"✅ User `{user_id}` has been removed from admins!")
            
            # Try to send notification
            try:
                await client.send_message(user_id, "⚠️ You have been removed from admin list!")
            except:
                pass
    
    except ValueError:
        await message.reply_text("❌ Invalid user ID!")
    except Exception as e:
        logger.error(f"Error managing admins: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("admins") & admin_only)
async def admins_command(client: Client, message: Message):
    """Get list of admins"""
    try:
        admins = await client.db.get_all_admins()
        
        text = "👮‍♂️ **Bot Admins:**\n\n"
        for i, admin_id in enumerate(admins, 1):
            if admin_id == Config.OWNER_ID:
                text += f"`{i}.` `{admin_id}` 👑 **(Owner)**\n"
            else:
                text += f"`{i}.` `{admin_id}`\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_admins")]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting admins: {e}")
        await message.reply_text("❌ Error getting admins list!")

@Client.on_message(filters.command(["dlt_time", "check_dlt_time"]) & admin_only)
async def auto_delete_commands(client: Client, message: Message):
    """Manage auto delete settings"""
    cmd = message.command[0]
    
    if cmd == "dlt_time":
        if len(message.command) < 2:
            await message.reply_text("❌ Usage: `/dlt_time <seconds>`\nExample: `/dlt_time 600` (10 minutes)")
            return
        
        try:
            seconds = int(message.command[1])
            if seconds < 60:
                await message.reply_text("❌ Minimum delete time is 60 seconds!")
                return
            
            await client.db.set_auto_delete_time(seconds)
            readable_time = get_readable_time(seconds)
            await message.reply_text(f"✅ Auto delete time set to `{readable_time}`")
            
        except ValueError:
            await message.reply_text("❌ Invalid time value!")
        except Exception as e:
            logger.error(f"Error setting delete time: {e}")
            await message.reply_text("❌ Error setting delete time!")
    
    else:  # check_dlt_time
        try:
            delete_time = await client.db.get_auto_delete_time()
            is_enabled = await client.db.is_auto_delete_enabled()
            
            readable_time = get_readable_time(delete_time)
            status = "✅ Enabled" if is_enabled else "❌ Disabled"
            
            text = f"""
🗑️ **Auto Delete Settings**

⏱️ **Delete Time:** `{readable_time}`
📊 **Status:** {status}
"""
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Enable" if not is_enabled else "❌ Disable", 
                                       callback_data=f"toggle_auto_delete_{not is_enabled}")
                ],
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_delete_settings")]
            ])
            
            await message.reply_text(text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error checking delete time: {e}")
            await message.reply_text("❌ Error getting delete settings!")

# Callback query handlers
@Client.on_callback_query(filters.regex("refresh_stats"))
async def refresh_stats_callback(client: Client, callback_query):
    """Refresh stats callback"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    await stats_command(client, callback_query.message)
    await callback_query.answer("✅ Stats refreshed!")

@Client.on_callback_query(filters.regex(r"toggle_auto_delete_(.+)"))
async def toggle_auto_delete_callback(client: Client, callback_query):
    """Toggle auto delete callback"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    enabled = callback_query.data.split("_")[-1] == "True"
    await client.db.set_auto_delete_enabled(enabled)
    
    status = "enabled" if enabled else "disabled"
    await callback_query.answer(f"✅ Auto delete {status}!")
    
    # Refresh the message
    await auto_delete_commands(client, callback_query.message)
