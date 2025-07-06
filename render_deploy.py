#!/usr/bin/env python3
"""
Discord Slowmode Bot - Render.com Deployment Script
"""

import os
import logging
from bot_simple import bot, scheduler

# Set up logging for render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for Render deployment"""
    try:
        # Get Discord token from environment
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            logger.error("DISCORD_BOT_TOKEN environment variable not set!")
            return
        
        logger.info("Starting Discord bot for Render deployment...")
        
        # Start the bot
        bot.run(token)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()