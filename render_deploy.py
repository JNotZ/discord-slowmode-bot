#!/usr/bin/env python3
"""
Discord Slowmode Bot - Render.com Deployment Script
"""

import os
import logging
import asyncio
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
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

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Render health checks"""
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Discord bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs to reduce noise
        pass

def start_health_server():
    """Start HTTP server for Render health checks"""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Starting health server on port {port}")
    server.serve_forever()

def main():
    """Main entry point for Render deployment"""
    try:
        # Get Discord token from environment
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            logger.error("DISCORD_BOT_TOKEN environment variable not set!")
            return
        
        logger.info("Starting Discord bot for Render deployment...")
        
        # Start health server in background thread
        health_thread = Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        # Start the bot (this will block)
        bot.run(token)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()