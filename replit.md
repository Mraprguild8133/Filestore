# Overview

This is a Telegram FileStore Bot built with Pyrogram that allows users to store and share files through unique links. The bot can automatically generate shareable links for files posted in configured channels, handle batch link generation for multiple files, and implement force subscription mechanisms. It features an in-memory database system and supports admin controls for broadcasting, user management, and channel configuration.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Pyrogram Client**: Uses the Pyrogram library for Telegram Bot API interactions with custom Bot class inheritance
- **Async Architecture**: Built entirely on asyncio for handling concurrent operations and multiple user requests
- **Plugin System**: Modular plugin architecture with automatic loading from the plugins directory

## Data Storage
- **In-Memory Database**: Custom Database class that stores all data in Python data structures (sets, dictionaries)
- **No Persistent Storage**: Data is stored in memory only - all information is lost when the bot restarts
- **Data Models**: Structured storage for users, files, batches, admin settings, and force subscription channels

## File Management
- **Link Generation**: Base64 encoding system for creating shareable file links
- **Batch Processing**: Support for generating single links that provide access to multiple files
- **Auto Link Generation**: Automatic link creation for files posted in configured channels
- **File Metadata**: Stores file names, sizes, types, hashes, and upload information

## Authentication & Authorization
- **Admin System**: Role-based access control with admin-only commands and features
- **User Banning**: Ability to ban users from accessing the bot
- **Force Subscription**: Optional mechanism requiring users to join specific channels before accessing files

## Message Handling
- **Command Processing**: Structured command handling for admin and user operations
- **Callback Query Handling**: Interactive button responses for confirmations and navigation
- **Flood Control**: Built-in mechanisms to handle Telegram API rate limiting
- **Error Handling**: Comprehensive error handling for blocked users and API limitations

## Admin Features
- **Broadcasting**: Mass message distribution to all bot users with confirmation system
- **Statistics**: Real-time bot usage statistics including user counts, file counts, and uptime
- **Channel Management**: Add/remove channels for force subscription
- **User Management**: Ban/unban users and view user statistics

# External Dependencies

## Core Dependencies
- **Pyrogram**: Primary Telegram client library for bot functionality
- **aiofiles**: Asynchronous file operations (imported but usage not visible in current files)

## Telegram Integration
- **Bot API**: Requires bot token, API ID, and API hash for Telegram integration
- **Channel Access**: Bot must be added as admin to channels for file management operations
- **Invite Link Generation**: Uses Telegram's chat invite link creation for force subscription

## Configuration Requirements
- **Environment Variables**: Relies on environment variables for all configuration (API credentials, admin IDs, channel IDs)
- **Channel Configuration**: Requires setup of storage channel ID and optional force subscription channels
- **Admin Configuration**: Configurable admin list and owner ID for access control

## Python Runtime
- **Python 3.11.5**: Specified runtime version in runtime.txt
- **Async/Await**: Heavily dependent on Python's asyncio capabilities for concurrent operations