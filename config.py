"""
Discord Slowmode Bot - Configuration Module
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BotConfig:
    """Configuration management for the Discord bot"""
    
    def __init__(self, config_file: str = "slowmode_config.json"):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        self.load_config()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config_data = json.load(f)
                    logger.info(f"Loaded configuration from {self.config_file}")
            else:
                logger.info(f"Config file {self.config_file} not found, using defaults")
                self.config_data = self.get_default_config()
                self.save_config()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            self.config_data = self.get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config_data = self.get_default_config()
            
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)
                logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "schedules": {
                "example_schedule": {
                    "channel_id": 123456789012345678,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "slowmode_seconds": 30,
                    "timezone": "UTC",
                    "enabled": False
                }
            },
            "settings": {
                "default_slowmode_seconds": 30,
                "default_timezone": "UTC",
                "log_level": "INFO"
            }
        }
        
    def get_schedules(self) -> Dict[str, Dict[str, Any]]:
        """Get all schedules from configuration"""
        schedules = self.config_data.get("schedules", {})
        
        # Filter out disabled schedules
        enabled_schedules = {}
        for schedule_id, schedule_data in schedules.items():
            if schedule_data.get("enabled", True):
                enabled_schedules[schedule_id] = schedule_data
                
        return enabled_schedules
        
    def add_schedule(self, schedule_id: str, channel_id: int, 
                    start_time: str, end_time: str, 
                    slowmode_seconds: int = 30, timezone: str = "UTC",
                    days: list = None, restore_seconds: int = 0) -> bool:
        """Add a new schedule to configuration"""
        try:
            if "schedules" not in self.config_data:
                self.config_data["schedules"] = {}
            
            # Default to all days if not specified
            if days is None:
                days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                
            self.config_data["schedules"][schedule_id] = {
                "channel_id": channel_id,
                "start_time": start_time,
                "end_time": end_time,
                "slowmode_seconds": slowmode_seconds,
                "timezone": timezone,
                "days": days,
                "restore_seconds": restore_seconds,
                "enabled": True
            }
            
            self.save_config()
            logger.info(f"Added schedule {schedule_id} to configuration")
            return True
            
        except Exception as e:
            logger.error(f"Error adding schedule to config: {e}")
            return False
            
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule from configuration"""
        try:
            if schedule_id in self.config_data.get("schedules", {}):
                del self.config_data["schedules"][schedule_id]
                self.save_config()
                logger.info(f"Removed schedule {schedule_id} from configuration")
                return True
            else:
                logger.warning(f"Schedule {schedule_id} not found in configuration")
                return False
                
        except Exception as e:
            logger.error(f"Error removing schedule from config: {e}")
            return False
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.config_data.get("settings", {}).get(key, default)
        
    def set_setting(self, key: str, value: Any):
        """Set a setting value"""
        if "settings" not in self.config_data:
            self.config_data["settings"] = {}
            
        self.config_data["settings"][key] = value
        self.save_config()
        
    def get_timezone_list(self) -> list:
        """Get list of supported timezones"""
        import pytz
        return sorted(pytz.all_timezones)
