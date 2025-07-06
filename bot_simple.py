"""
Discord Slowmode Bot - Simplified Version
"""

import logging
import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

from scheduler import SlowmodeScheduler
from config import BotConfig

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Create bot instance
bot = commands.Bot(command_prefix='!sm ', intents=intents, help_command=None)

# Initialize components
config = BotConfig()
scheduler = SlowmodeScheduler(bot)

@bot.event
async def on_ready():
    """Called when the bot has logged in and is ready"""
    logger.info(f'Bot logged in as {bot.user} (ID: {bot.user.id if bot.user else "Unknown"})')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    logger.info(f"Registered commands: {[cmd.name for cmd in bot.commands]}")
    
    # Start the scheduler
    await scheduler.start()
    
    # Load schedules from config
    schedules = config.get_schedules()
    for schedule_id, schedule_data in schedules.items():
        await scheduler.add_schedule(
            schedule_id=schedule_id,
            channel_id=schedule_data['channel_id'],
            start_time=schedule_data['start_time'],
            end_time=schedule_data['end_time'],
            slowmode_seconds=schedule_data.get('slowmode_seconds', 30),
            timezone=schedule_data.get('timezone', 'UTC')
        )
    logger.info(f"Loaded {len(schedules)} slowmode schedules")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="channel slowmodes"
        )
    )

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    if message.author == bot.user:
        return
        
    # Log command attempts for debugging
    if message.content.startswith('!sm'):
        logger.info(f"Command received: '{message.content}' from {message.author}")
        logger.info(f"Registered commands: {[cmd.name for cmd in bot.commands]}")
        
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        logger.info(f"Command not found: {ctx.message.content}")
        return
    elif isinstance(error, commands.MissingPermissions):
        logger.info(f"Missing permissions for command: {ctx.message.content}")
        await ctx.send("❌ You need administrator permissions to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        logger.info(f"Bot missing permissions for command: {ctx.message.content}")
        await ctx.send("❌ I don't have the required permissions to execute this command.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")

@bot.command(name='ping')
async def ping(ctx):
    """Test command to check if bot is responding"""
    await ctx.send("🏓 Pong! Bot is online and working!")

@bot.command(name='help')
async def help_cmd(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="Discord Slowmode Bot Commands",
        description="All commands require administrator permissions",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="!sm ping",
        value="Test if bot is responding",
        inline=False
    )
    
    embed.add_field(
        name="!sm add_schedule #channel 09:00 17:00 30 [days] [restore]",
        value="Add slowmode schedule\ndays: mon,tue,wed,thu,fri,sat,sun or 'all' (default: all)\nrestore: slowmode to restore to or 'current' (default: current)",
        inline=False
    )
    
    embed.add_field(
        name="!sm list_schedules",
        value="List all active schedules",
        inline=False
    )
    
    embed.add_field(
        name="!sm remove_schedule #channel 09:00 17:00",
        value="Remove a specific schedule",
        inline=False
    )
    
    embed.add_field(
        name="!sm test_slowmode #channel 30",
        value="Test slowmode settings immediately",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='add_schedule')
@commands.has_permissions(administrator=True)
async def add_schedule(ctx, channel: discord.TextChannel, start_time: str, end_time: str, slowmode_seconds: int = 30, days: str = "all", restore_seconds: str = "current"):
    """Add a new slowmode schedule with day-specific and restore options"""
    try:
        # Parse and validate days
        valid_days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'all']
        if days.lower() == 'all':
            selected_days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        else:
            selected_days = [day.strip().lower() for day in days.split(',')]
            for day in selected_days:
                if day not in valid_days[:-1]:  # exclude 'all' from validation
                    await ctx.send(f"❌ Invalid day: {day}. Use: mon,tue,wed,thu,fri,sat,sun")
                    return
        
        # Handle restore_seconds parameter
        if restore_seconds == "current":
            restore_seconds_value = channel.slowmode_delay
        else:
            try:
                restore_seconds_value = int(restore_seconds)
            except (ValueError, TypeError):
                restore_seconds_value = channel.slowmode_delay
            
        # Generate schedule ID with days
        days_str = ",".join(sorted(selected_days))
        schedule_id = f"{ctx.guild.id}_{channel.id}_{start_time}_{end_time}_{days_str}"
        
        # Add schedule
        success = await scheduler.add_schedule(
            schedule_id=schedule_id,
            channel_id=channel.id,
            start_time=start_time,
            end_time=end_time,
            slowmode_seconds=slowmode_seconds,
            days=selected_days,
            restore_seconds=restore_seconds_value,
            timezone='UTC'
        )
        
        # Also add to config for persistence
        if success:
            config.add_schedule(
                schedule_id=schedule_id,
                channel_id=channel.id,
                start_time=start_time,
                end_time=end_time,
                slowmode_seconds=slowmode_seconds,
                days=selected_days,
                restore_seconds=restore_seconds_value,
                timezone='UTC'
            )
            
            embed = discord.Embed(
                title="✅ Schedule Added",
                description=f"Added slowmode schedule for {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Time", value=f"{start_time} - {end_time} UTC", inline=True)
            embed.add_field(name="Slowmode", value=f"{slowmode_seconds} seconds", inline=True)
            embed.add_field(name="Days", value=days_str.replace(',', ', '), inline=True)
            embed.add_field(name="Restore to", value=f"{restore_seconds} seconds", inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Added schedule {schedule_id} by {ctx.author}")
        else:
            await ctx.send("❌ Failed to add schedule. Check the time format (HH:MM).")
            
    except Exception as e:
        logger.error(f"Error adding schedule: {e}")
        await ctx.send(f"❌ Error adding schedule: {str(e)}")

@bot.command(name='list_schedules')
@commands.has_permissions(administrator=True)
async def list_schedules(ctx):
    """List all active slowmode schedules for this server"""
    try:
        schedules = scheduler.get_guild_schedules(ctx.guild.id)
        
        if not schedules:
            await ctx.send("No active slowmode schedules found for this server.")
            return
            
        embed = discord.Embed(
            title="Active Slowmode Schedules",
            color=discord.Color.blue()
        )
        
        for schedule_id, schedule_data in schedules.items():
            channel = bot.get_channel(schedule_data['channel_id'])
            channel_name = getattr(channel, 'name', f"Unknown ({schedule_data['channel_id']})")
            
            embed.add_field(
                name=f"#{channel_name}",
                value=f"Start: {schedule_data['start_time']} ({schedule_data['slowmode_seconds']}s)\n"
                      f"End: {schedule_data['end_time']} (disabled)",
                inline=True
            )
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        await ctx.send(f"❌ Error listing schedules: {str(e)}")

@bot.command(name="remove_schedule")
async def remove_schedule(ctx, channel: discord.TextChannel, start_time: str, end_time: str):
    """Remove a slowmode schedule"""
    # Check if user has administrator permissions
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to use this command!")
        return
    
    try:
        # Load current config
        config = BotConfig()
        schedules = config.get_schedules()
        
        # Find matching schedule(s) by channel, start_time, and end_time
        matching_schedules = []
        for schedule_id, schedule_data in schedules.items():
            if (schedule_data.get('channel_id') == channel.id and 
                schedule_data.get('start_time') == start_time and 
                schedule_data.get('end_time') == end_time):
                matching_schedules.append(schedule_id)
        
        if not matching_schedules:
            await ctx.send(f"❌ No schedule found for {channel.mention} from {start_time} to {end_time}")
            return
        
        # Remove all matching schedules (there should typically be only one)
        removed_count = 0
        for schedule_id in matching_schedules:
            # Remove from scheduler
            removed = await scheduler.remove_schedule(schedule_id)
            
            if removed:
                # Remove from config
                config.remove_schedule(schedule_id)
                removed_count += 1
                logger.info(f"Removed schedule {schedule_id} by {ctx.author}")
        
        if removed_count > 0:
            embed = discord.Embed(
                title="✅ Schedule Removed",
                description=f"Removed {removed_count} slowmode schedule(s) for {channel.mention}",
                color=discord.Color.red()
            )
            embed.add_field(name="Time", value=f"{start_time} - {end_time} UTC", inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Failed to remove schedule for {channel.mention}")
            
    except Exception as e:
        logger.error(f"Error removing schedule: {e}")
        await ctx.send(f"❌ Error removing schedule: {str(e)}")

@bot.command(name="test_slowmode")
async def test_slowmode(ctx, channel: discord.TextChannel, slowmode_seconds: int):
    """Test setting slowmode for a channel"""
    # Check if user has administrator permissions
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to use this command!")
        return
    
    try:
        # Validate slowmode_seconds
        if slowmode_seconds < 0 or slowmode_seconds > 21600:  # Discord max is 6 hours
            await ctx.send("❌ Slowmode must be between 0 and 21600 seconds (6 hours)")
            return
        
        # Test setting slowmode
        success = await set_channel_slowmode(channel.id, slowmode_seconds)
        
        if success:
            slowmode_text = f"{slowmode_seconds} seconds" if slowmode_seconds > 0 else "disabled"
            
            embed = discord.Embed(
                title="✅ Test Slowmode Applied",
                description=f"Successfully set slowmode to {slowmode_text} for {channel.mention}",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Test slowmode set to {slowmode_seconds} seconds for {channel.name} by {ctx.author}")
        else:
            await ctx.send(f"❌ Failed to set slowmode for {channel.mention}. Check bot permissions.")
            
    except Exception as e:
        logger.error(f"Error testing slowmode: {e}")
        await ctx.send(f"❌ Error testing slowmode: {str(e)}")

async def set_channel_slowmode(channel_id: int, slowmode_seconds: int) -> bool:
    """Set slowmode for a specific channel"""
    try:
        channel = bot.get_channel(channel_id)
        
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return False
            
        if not isinstance(channel, discord.TextChannel):
            logger.error(f"Channel {channel_id} is not a text channel")
            return False
            
        # Check if bot has permission to manage channels
        if not channel.permissions_for(channel.guild.me).manage_channels:
            logger.error(f"Bot lacks permission to manage channel {channel_id}")
            return False
            
        # Set slowmode
        await channel.edit(slowmode_delay=slowmode_seconds)
        
        slowmode_text = f"{slowmode_seconds} seconds" if slowmode_seconds > 0 else "disabled"
        logger.info(f"Set slowmode to {slowmode_text} for channel #{channel.name} in {channel.guild.name}")
        
        return True
        
    except discord.Forbidden:
        logger.error(f"Permission denied when setting slowmode for channel {channel_id}")
        return False
    except discord.HTTPException as e:
        logger.error(f"HTTP error when setting slowmode for channel {channel_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error setting slowmode for channel {channel_id}: {e}")
        return False

# Make the function available to scheduler
bot.set_channel_slowmode = set_channel_slowmode

if __name__ == "__main__":
    # Get Discord bot token from environment
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN environment variable is required!")
        exit(1)
    
    try:
        logger.info("Starting Discord Slowmode Bot...")
        bot.run(bot_token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot encountered an error: {e}")