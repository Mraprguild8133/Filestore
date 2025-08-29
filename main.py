# ... (previous imports and setup)

def main():
    """Main function to run the bot"""
    global bot_instance
    
    # Get port from environment (for Render.com deployment)
    PORT = int(os.environ.get("PORT", 8000))
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    debug = ENVIRONMENT == "development"
    
    # Set up the bot in the main thread (for simpler deployment)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_instance = loop.run_until_complete(setup_bot())
    
    # Start polling in the background
    polling_task = loop.create_task(bot_instance.start_polling())
    
    logger.info(f"Starting Flask app on port {PORT}")
    logger.info(f"Bot @{bot_instance.bot_username} is ready to receive messages")
    
    try:
        # Run Flask in the main thread (this will block)
        from waitress import serve  # For production deployment
        if debug:
            app.run(host='0.0.0.0', port=PORT, debug=debug)
        else:
            serve(app, host='0.0.0.0', port=PORT)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        polling_task.cancel()
        loop.run_until_complete(bot_instance.shutdown())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
