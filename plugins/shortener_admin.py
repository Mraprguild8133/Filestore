#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shortener management plugin for admin commands
"""

import logging
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from shortener import shortener

logger = logging.getLogger(__name__)

# Admin filter
def admin_filter(_, __, message):
    return message.from_user.id in Config.ADMINS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("shortener") & admin_only)
async def shortener_settings_command(client: Client, message: Message):
    """Manage shortener settings"""
    try:
        current_site = shortener.get_current_site()
        is_enabled = shortener.is_enabled()
        requires_key = shortener.site_requires_key(current_site)
        has_key = bool(Config.SHORTENER_API_KEY)
        
        status_emoji = "✅" if is_enabled else "❌"
        key_status = "✅ Set" if has_key else "❌ Not Set"
        
        response_text = f"""
🔗 **URL Shortener Settings**

📊 **Status:** {status_emoji} {'Enabled' if is_enabled else 'Disabled'}
🌐 **Current Site:** `{current_site}`
🔑 **API Key:** {key_status}
⚙️ **Key Required:** {'Yes' if requires_key else 'No'}

📝 **Available Commands:**
• `/shortener_toggle` - Enable/disable shortener
• `/shortener_site <site>` - Change shortener site
• `/shortener_key <api_key>` - Set API key
• `/shortener_sites` - View all supported sites
• `/shortener_test <url>` - Test shortener with a URL
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Enable" if not is_enabled else "❌ Disable", 
                                   callback_data=f"toggle_shortener_{not is_enabled}"),
                InlineKeyboardButton("🌐 Change Site", callback_data="shortener_change_site")
            ],
            [
                InlineKeyboardButton("📝 Supported Sites", callback_data="shortener_show_sites"),
                InlineKeyboardButton("🧪 Test", callback_data="shortener_test_prompt")
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_shortener_settings")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing shortener settings: {e}")
        await message.reply_text("❌ Error getting shortener settings!")

@Client.on_message(filters.command("shortener_toggle") & admin_only)
async def toggle_shortener_command(client: Client, message: Message):
    """Toggle shortener on/off"""
    try:
        current_status = shortener.is_enabled()
        new_status = not current_status
        
        # Update environment variable (note: this is temporary for current session)
        os.environ["SHORTENER_ENABLED"] = str(new_status).lower()
        Config.SHORTENER_ENABLED = new_status
        shortener.enabled = new_status
        
        status_text = "✅ Enabled" if new_status else "❌ Disabled"
        action_text = "enabled" if new_status else "disabled"
        
        response_text = f"""
🔄 **Shortener Status Updated!**

📊 **New Status:** {status_text}
🌐 **Current Site:** `{shortener.get_current_site()}`

📝 **Effect:** URL shortener has been {action_text}
"""
        
        if new_status and shortener.site_requires_key(shortener.get_current_site()) and not Config.SHORTENER_API_KEY:
            response_text += "\n⚠️ **Warning:** Current site requires API key but none is set!\nUse `/shortener_key <your_api_key>` to set it."
        
        await message.reply_text(response_text)
        logger.info(f"Shortener toggled to {new_status} by user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error toggling shortener: {e}")
        await message.reply_text("❌ Error toggling shortener!")

@Client.on_message(filters.command("shortener_site") & admin_only)
async def change_shortener_site_command(client: Client, message: Message):
    """Change shortener site"""
    if len(message.command) < 2:
        supported_sites = shortener.get_supported_sites()
        sites_text = "\n".join([f"• `{site}`" for site in supported_sites])
        
        await message.reply_text(
            f"❌ **Usage:** `/shortener_site <site_name>`\n\n"
            f"**Supported Sites:**\n{sites_text}\n\n"
            f"**Example:** `/shortener_site tinyurl.com`"
        )
        return
    
    new_site = message.command[1].lower()
    supported_sites = shortener.get_supported_sites()
    
    if new_site not in supported_sites:
        await message.reply_text(
            f"❌ **Unsupported site:** `{new_site}`\n\n"
            f"Use `/shortener_sites` to see all supported sites."
        )
        return
    
    try:
        # Update environment variable
        os.environ["SHORTENER_SITE"] = new_site
        Config.SHORTENER_SITE = new_site
        shortener.site = new_site
        
        requires_key = shortener.site_requires_key(new_site)
        has_key = bool(Config.SHORTENER_API_KEY)
        
        response_text = f"""
✅ **Shortener Site Updated!**

🌐 **New Site:** `{new_site}`
🔑 **API Key Required:** {'Yes' if requires_key else 'No'}
🔑 **API Key Status:** {'✅ Set' if has_key else '❌ Not Set'}
"""
        
        if requires_key and not has_key:
            response_text += "\n⚠️ **Warning:** This site requires an API key!\nUse `/shortener_key <your_api_key>` to set it."
        
        await message.reply_text(response_text)
        logger.info(f"Shortener site changed to {new_site} by user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error changing shortener site: {e}")
        await message.reply_text("❌ Error changing shortener site!")

@Client.on_message(filters.command("shortener_key") & admin_only)
async def set_shortener_key_command(client: Client, message: Message):
    """Set shortener API key"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/shortener_key <api_key>`\n\n"
            "📝 **Note:** The API key will be stored securely.\n"
            "🗑️ **To remove:** `/shortener_key remove`"
        )
        return
    
    api_key = message.command[1]
    
    try:
        if api_key.lower() == "remove":
            # Remove API key
            os.environ["SHORTENER_API_KEY"] = ""
            Config.SHORTENER_API_KEY = ""
            shortener.api_key = ""
            
            await message.reply_text("🗑️ **API Key Removed!**\n\nShortener API key has been cleared.")
        else:
            # Set API key
            os.environ["SHORTENER_API_KEY"] = api_key
            Config.SHORTENER_API_KEY = api_key
            shortener.api_key = api_key
            
            # Mask the key for display
            masked_key = api_key[:8] + "*" * (len(api_key) - 8) if len(api_key) > 8 else "*" * len(api_key)
            
            await message.reply_text(
                f"✅ **API Key Updated!**\n\n"
                f"🔑 **Key:** `{masked_key}`\n"
                f"🌐 **Site:** `{shortener.get_current_site()}`"
            )
        
        # Delete the command message for security
        try:
            await message.delete()
        except:
            pass
        
        logger.info(f"Shortener API key updated by user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error setting shortener key: {e}")
        await message.reply_text("❌ Error setting API key!")

@Client.on_message(filters.command("shortener_sites") & admin_only)
async def list_shortener_sites_command(client: Client, message: Message):
    """List all supported shortener sites"""
    try:
        supported_sites = Config.SUPPORTED_SHORTENERS
        current_site = shortener.get_current_site()
        
        response_text = "🌐 **Supported Shortener Sites**\n\n"
        
        for site, config in supported_sites.items():
            status = "🔸" if site == current_site else "◦"
            key_req = "🔑" if config["requires_key"] else "🆓"
            
            response_text += f"{status} **{site}** {key_req}\n"
            if config["requires_key"]:
                response_text += f"    Requires API Key\n"
            response_text += f"    {config['api_url']}\n\n"
        
        response_text += "**Legend:**\n"
        response_text += "🔸 Current site\n"
        response_text += "🔑 Requires API key\n"
        response_text += "🆓 Free (no API key needed)"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Settings", callback_data="refresh_shortener_settings")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error listing shortener sites: {e}")
        await message.reply_text("❌ Error getting supported sites!")

@Client.on_message(filters.command("shortener_test") & admin_only)
async def test_shortener_command(client: Client, message: Message):
    """Test shortener with a URL"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Usage:** `/shortener_test <url>`\n\n"
            "**Example:** `/shortener_test https://google.com`"
        )
        return
    
    test_url = message.command[1]
    
    if not test_url.startswith(("http://", "https://")):
        test_url = "https://" + test_url
    
    try:
        status_msg = await message.reply_text("🔄 Testing shortener... Please wait!")
        
        # Test the shortener
        shortened_url = await shortener.shorten_url(test_url)
        
        if shortened_url != test_url:
            response_text = f"""
✅ **Shortener Test Successful!**

🌐 **Service:** `{shortener.get_current_site()}`
📎 **Original:** `{test_url}`
🔗 **Shortened:** `{shortened_url}`

✅ **Status:** Working perfectly!
"""
        else:
            response_text = f"""
❌ **Shortener Test Failed!**

🌐 **Service:** `{shortener.get_current_site()}`
📎 **Test URL:** `{test_url}`

❌ **Result:** URL was not shortened
🔍 **Possible Issues:**
• API key might be invalid
• Service might be down
• URL format might be invalid
"""
        
        await status_msg.edit_text(response_text, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error testing shortener: {e}")
        await message.reply_text(f"❌ Error testing shortener: {str(e)}")

# Callback query handlers
@Client.on_callback_query(filters.regex(r"toggle_shortener_(.+)"))
async def toggle_shortener_callback(client: Client, callback_query: CallbackQuery):
    """Toggle shortener callback"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    enabled = callback_query.data.split("_")[-1] == "True"
    
    # Update settings
    os.environ["SHORTENER_ENABLED"] = str(enabled).lower()
    Config.SHORTENER_ENABLED = enabled
    shortener.enabled = enabled
    
    status = "enabled" if enabled else "disabled"
    await callback_query.answer(f"✅ Shortener {status}!")
    
    # Refresh the settings
    await shortener_settings_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("refresh_shortener_settings"))
async def refresh_shortener_settings_callback(client: Client, callback_query: CallbackQuery):
    """Refresh shortener settings"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    await callback_query.answer("🔄 Settings refreshed!")
    await shortener_settings_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("shortener_show_sites"))
async def shortener_show_sites_callback(client: Client, callback_query: CallbackQuery):
    """Show supported sites"""
    if callback_query.from_user.id not in Config.ADMINS:
        await callback_query.answer("❌ Only admins can use this!", show_alert=True)
        return
    
    await callback_query.answer()
    await list_shortener_sites_command(client, callback_query.message)

@Client.on_callback_query(filters.regex("shortener_change_site"))
async def shortener_change_site_callback(client: Client, callback_query: CallbackQuery):
    """Show change site help"""
    help_text = """
🌐 **Change Shortener Site**

**Usage:** `/shortener_site <site_name>`

**Popular Free Sites:**
• `tinyurl.com` - No API key needed
• `is.gd` - No API key needed  
• `v.gd` - No API key needed
• `gg.gg` - No API key needed

**Premium Sites (require API key):**
• `bit.ly` - Popular, reliable
• `short.io` - Custom domains
• `rebrandly.com` - Branded links
• `cutt.ly` - Analytics included

**Example:** `/shortener_site tinyurl.com`
"""
    
    await callback_query.message.edit_text(help_text)
    await callback_query.answer()

@Client.on_callback_query(filters.regex("shortener_test_prompt"))
async def shortener_test_prompt_callback(client: Client, callback_query: CallbackQuery):
    """Show test prompt"""
    help_text = """
🧪 **Test Shortener**

**Usage:** `/shortener_test <url>`

**Examples:**
• `/shortener_test https://google.com`
• `/shortener_test https://github.com`
• `/shortener_test google.com` (will add https://)

This will test if your current shortener configuration is working properly.
"""
    
    await callback_query.message.edit_text(help_text)
    await callback_query.answer()