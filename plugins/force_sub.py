#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force subscription management plugin
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import ChatAdminRequired, ChannelInvalid, PeerIdInvalid
from config import Config

logger = logging.getLogger(__name__)

# Admin filter
def admin_filter(_, __, message):
    return message.from_user.id in Config.ADMINS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("addchnl") & admin_only)
async def add_channel_command(client: Client, message: Message):
    """Add a channel for force subscription"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/addchnl <channel_id_or_username>`\n\n"
            "**Examples:**\n"
            "`/addchnl -1001234567890`\n"
            "`/addchnl @channel_username`\n\n"
            "📝 **Note:** Make sure I'm added as admin in the channel!"
        )
        return
    
    channel_input = message.command[1]
    
    try:
        # Try to get channel info
        if channel_input.startswith('@'):
            channel = await client.get_chat(channel_input)
        else:
            try:
                channel_id = int(channel_input)
                channel = await client.get_chat(channel_id)
            except ValueError:
                await message.reply_text("❌ Invalid channel ID! Please provide a valid number or username.")
                return
        
        # Check if bot is admin in the channel
        try:
            bot_member = await client.get_chat_member(channel.id, client.id)
            if not bot_member.privileges or not bot_member.privileges.can_invite_users:
                await message.reply_text(
                    f"❌ I don't have enough permissions in **{channel.title}**!\n\n"
                    "Please make sure I'm added as admin with 'Invite Users' permission."
                )
                return
        except Exception as e:
            await message.reply_text(
                f"❌ Error checking permissions in **{channel.title}**: {str(e)}\n\n"
                "Please make sure I'm added as admin in the channel!"
            )
            return
        
        # Check if channel is already added
        force_sub_channels = await client.db.get_force_sub_channels()
        if channel.id in force_sub_channels:
            await message.reply_text(f"⚠️ **{channel.title}** is already in the force subscription list!")
            return
        
        # Add channel to force subscription
        await client.db.add_force_sub_channel(channel.id)
        
        # Create response
        channel_link = f"https://t.me/{channel.username}" if channel.username else f"Channel ID: {channel.id}"
        
        response_text = f"""
✅ **Channel Added Successfully!**

📢 **Channel:** {channel.title}
🔗 **Link:** {channel_link}
👥 **Members:** {channel.members_count if hasattr(channel, 'members_count') else 'Unknown'}

📊 **Total Force Sub Channels:** {len(force_sub_channels) + 1}
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 View All Channels", callback_data="list_fsub_channels")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_fsub_settings")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
        logger.info(f"Added force sub channel {channel.id} ({channel.title}) by user {message.from_user.id}")
        
    except ChannelInvalid:
        await message.reply_text("❌ Invalid channel! Please check the channel ID or username.")
    except PeerIdInvalid:
        await message.reply_text("❌ Invalid channel! Please check the channel ID or username.")
    except ChatAdminRequired:
        await message.reply_text("❌ I need to be an admin in the channel to add it for force subscription!")
    except Exception as e:
        logger.error(f"Error adding force sub channel: {e}")
        await message.reply_text(f"❌ Error adding channel: {str(e)}")

@Client.on_message(filters.command("delchnl") & admin_only)
async def delete_channel_command(client: Client, message: Message):
    """Remove a channel from force subscription"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/delchnl <channel_id_or_username>`\n\n"
            "**Examples:**\n"
            "`/delchnl -1001234567890`\n"
            "`/delchnl @channel_username`\n\n"
            "💡 **Tip:** Use `/listchnl` to see all added channels."
        )
        return
    
    channel_input = message.command[1]
    
    try:
        # Try to get channel info
        if channel_input.startswith('@'):
            channel = await client.get_chat(channel_input)
            channel_id = channel.id
        else:
            try:
                channel_id = int(channel_input)
                channel = await client.get_chat(channel_id)
            except ValueError:
                await message.reply_text("❌ Invalid channel ID! Please provide a valid number or username.")
                return
        
        # Check if channel is in force subscription list
        force_sub_channels = await client.db.get_force_sub_channels()
        if channel_id not in force_sub_channels:
            await message.reply_text(f"⚠️ **{channel.title}** is not in the force subscription list!")
            return
        
        # Remove channel from force subscription
        await client.db.remove_force_sub_channel(channel_id)
        
        # Create response
        response_text = f"""
✅ **Channel Removed Successfully!**

📢 **Channel:** {channel.title}
🗑️ **Status:** Removed from force subscription

📊 **Remaining Channels:** {len(force_sub_channels) - 1}
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 View Remaining Channels", callback_data="list_fsub_channels")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_fsub_settings")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard)
        
        logger.info(f"Removed force sub channel {channel_id} ({channel.title}) by user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error removing force sub channel: {e}")
        await message.reply_text(f"❌ Error removing channel: {str(e)}")

@Client.on_message(filters.command("listchnl") & admin_only)
async def list_channels_command(client: Client, message: Message):
    """List all force subscription channels"""
    try:
        force_sub_channels = await client.db.get_force_sub_channels()
        
        if not force_sub_channels:
            await message.reply_text(
                "📝 **No Force Subscription Channels**\n\n"
                "Use `/addchnl <channel_id>` to add channels for force subscription."
            )
            return
        
        response_text = f"📝 **Force Subscription Channels** ({len(force_sub_channels)})\n\n"
        
        for i, channel_id in enumerate(force_sub_channels, 1):
            try:
                channel = await client.get_chat(channel_id)
                channel_link = f"https://t.me/{channel.username}" if channel.username else "Private Channel"
                response_text += f"`{i}.` **{channel.title}**\n"
                response_text += f"    🆔 `{channel_id}`\n"
                response_text += f"    🔗 {channel_link}\n"
                response_text += f"    👥 {channel.members_count if hasattr(channel, 'members_count') else 'Unknown'} members\n\n"
            except Exception as e:
                response_text += f"`{i}.` **Unknown Channel**\n"
                response_text += f"    🆔 `{channel_id}`\n"
                response_text += f"    ⚠️ Error: {str(e)}\n\n"
        
        # Get force sub status
        is_enabled = await client.db.is_force_sub_enabled()
        status_emoji = "✅" if is_enabled else "❌"
        response_text += f"📊 **Force Sub Status:** {status_emoji} {'Enabled' if is_enabled else 'Disabled'}"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Enable" if not is_enabled else "❌ Disable", 
                                   callback_data=f"toggle_fsub_{not is_enabled}"),
                InlineKeyboardButton("🔄 Refresh", callback_data="list_fsub_channels")
            ],
            [InlineKeyboardButton("🗑️ Clear All", callback_data="clear_all_fsub_channels")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error listing force sub channels: {e}")
        await message.reply_text("❌ Error getting channel list!")

@Client.on_message(filters.command("fsub_mode") & admin_only)
async def fsub_mode_command(client: Client, message: Message):
    """Toggle force subscription mode"""
    try:
        current_status = await client.db.is_force_sub_enabled()
        new_status = not current_status
        
        await client.db.set_force_sub_enabled(new_status)
        
        status_text = "✅ Enabled" if new_status else "❌ Disabled"
        action_text = "enabled" if new_status else "disabled"
        
        force_sub_channels = await client.db.get_force_sub_channels()
        
        response_text = f"""
🔄 **Force Subscription Mode Updated!**

📊 **Status:** {status_text}
📢 **Channels:** {len(force_sub_channels)}

📝 **Effect:** Force subscription has been {action_text}
"""
        
        if new_status and not force_sub_channels:
            response_text += "\n⚠️ **Warning:** No channels added for force subscription!\nUse `/addchnl` to add channels."
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📝 View Channels", callback_data="list_fsub_channels"),
                InlineKeyboardButton("➕ Add Channel", callback_data="show_addchnl_help")
            ]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard)
        
        logger.info(f"Force sub mode toggled to {new_status} by user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error toggling force sub mode: {e}")
        await message.reply_text("❌ Error toggling force subscription mode!")

@Client.on_message(filters.command("delreq") & admin_only)
async def delete_requests_command(client: Client, message: Message):
    """Remove users who left channels and are not getting force sub requests"""
    try:
        force_sub_channels = await client.db.get_force_sub_channels()
        
        if not force_sub_channels:
            await message.reply_text("❌ No force subscription channels configured!")
            return
        
        all_users = await client.db.get_all_users()
        
        status_msg = await message.reply_text("🔄 Checking user subscriptions... Please wait!")
        
        removed_users = []
        checked_count = 0
        
        for user_id in all_users:
            try:
                # Check if user is still subscribed to all channels
                for channel_id in force_sub_channels:
                    try:
                        member = await client.get_chat_member(channel_id, user_id)
                        if member.status in ["kicked", "left"]:
                            # User left the channel, remove from database
                            await client.db.remove_user(user_id)
                            removed_users.append(user_id)
                            break
                    except Exception:
                        # User not found in channel, remove from database
                        await client.db.remove_user(user_id)
                        removed_users.append(user_id)
                        break
                
                checked_count += 1
                
                # Update progress every 50 users
                if checked_count % 50 == 0:
                    await status_msg.edit_text(
                        f"🔄 Checking user subscriptions...\n\n"
                        f"✅ Checked: {checked_count}/{len(all_users)}\n"
                        f"🗑️ Removed: {len(removed_users)}"
                    )
                
            except Exception as e:
                logger.error(f"Error checking user {user_id}: {e}")
                continue
        
        # Final result
        response_text = f"""
✅ **Cleanup Completed!**

👥 **Users Checked:** {checked_count}
🗑️ **Users Removed:** {len(removed_users)}
📊 **Remaining Users:** {len(all_users) - len(removed_users)}

📝 **Note:** Removed users who left force subscription channels.
"""
        
        await status_msg.edit_text(response_text)
        
        logger.info(f"Cleanup completed: {len(removed_users)} users removed by {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        await message.reply_text("❌ Error during cleanup process!")

# Callback query handlers
@Client.on_callback_query(filters.regex(r"toggle_fsub_(.+)"))
async def toggle_fsub_callback(client: Client, callback_query: CallbackQuery):
    """Toggle force subscription callback"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    enabled = callback_query.data.split("_")[-1] == "True"
    await client.db.set_force_sub_enabled(enabled)
    
    status = "enabled" if enabled else "disabled"
    await callback_query.answer(f"✅ Force subscription {status}!")
    
    # Refresh the message
    await list_channels_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("list_fsub_channels"))
async def list_fsub_channels_callback(client: Client, callback_query: CallbackQuery):
    """List force sub channels callback"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    await callback_query.answer("🔄 Refreshing...")
    await list_channels_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("clear_all_fsub_channels"))
async def clear_all_fsub_channels_callback(client: Client, callback_query: CallbackQuery):
    """Clear all force sub channels callback"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    # Confirmation keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Clear All", callback_data="confirm_clear_fsub"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_clear_fsub")
        ]
    ])
    
    force_sub_channels = await client.db.get_force_sub_channels()
    
    await callback_query.message.edit_text(
        f"⚠️ **Confirm Action**\n\n"
        f"Are you sure you want to remove all {len(force_sub_channels)} force subscription channels?\n\n"
        f"❌ This action cannot be undone!",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("confirm_clear_fsub"))
async def confirm_clear_fsub_callback(client: Client, callback_query: CallbackQuery):
    """Confirm clear all force sub channels"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    try:
        force_sub_channels = await client.db.get_force_sub_channels()
        count = len(force_sub_channels)
        
        # Clear all channels
        for channel_id in force_sub_channels:
            await client.db.remove_force_sub_channel(channel_id)
        
        await callback_query.message.edit_text(
            f"✅ **All Channels Cleared!**\n\n"
            f"🗑️ Removed {count} force subscription channels.\n"
            f"📊 Current channels: 0"
        )
        
        await callback_query.answer("✅ All channels cleared!")
        logger.info(f"Cleared all force sub channels by user {callback_query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error clearing force sub channels: {e}")
        await callback_query.answer("❌ Error clearing channels!", show_alert=True)

@Client.on_callback_query(filters.regex("cancel_clear_fsub"))
async def cancel_clear_fsub_callback(client: Client, callback_query: CallbackQuery):
    """Cancel clear all force sub channels"""
    await callback_query.answer("❌ Action cancelled!")
    await list_channels_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("show_addchnl_help"))
async def show_addchnl_help_callback(client: Client, callback_query: CallbackQuery):
    """Show add channel help"""
    help_text = """
📝 **Add Channel for Force Subscription**

**Usage:** `/addchnl <channel_id_or_username>`

**Examples:**
• `/addchnl -1001234567890`
• `/addchnl @channel_username`

**Requirements:**
• Bot must be admin in the channel
• Bot needs 'Invite Users' permission
• Channel can be public or private

**Tips:**
• Get channel ID from channel info
• Use @username for public channels
• Make sure bot has proper permissions
"""
    
    await callback_query.message.edit_text(help_text)
    await callback_query.answer()

@Client.on_callback_query(filters.regex("refresh_fsub_settings"))
async def refresh_fsub_settings_callback(client: Client, callback_query: CallbackQuery):
    """Refresh force sub settings"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    await callback_query.answer("🔄 Settings refreshed!")
    await list_channels_command(client, callback_query.message)
