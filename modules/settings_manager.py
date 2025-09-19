"""
Settings Manager for Chatbot
Handles runtime configuration changes for authorized users
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages bot settings and configuration"""
    
    def __init__(self):
        self.settings_file = os.getenv("SETTINGS_FILE_PATH", "./settings.json")
        self.persistence_enabled = os.getenv("ENABLE_SETTINGS_MANAGEMENT", "true").lower() == "true"
        
        # Authorized users for each platform
        self.authorized_users = {
            'matrix': os.getenv("SETTINGS_AUTHORIZED_MATRIX_USERS", "").split(",") if os.getenv("SETTINGS_AUTHORIZED_MATRIX_USERS") else [],
            'discord': os.getenv("SETTINGS_AUTHORIZED_DISCORD_USERS", "").split(",") if os.getenv("SETTINGS_AUTHORIZED_DISCORD_USERS") else [],
            'telegram': os.getenv("SETTINGS_AUTHORIZED_TELEGRAM_USERS", "").split(",") if os.getenv("SETTINGS_AUTHORIZED_TELEGRAM_USERS") else []
        }
        
        # Define configurable settings with their types and descriptions
        self.configurable_settings = {
            'llm_temperature': {
                'type': 'float',
                'min': 0.0,
                'max': 1.0,
                'description': 'LLM temperature (0.0-1.0, higher = more creative)',
                'env_var': 'OLLAMA_TEMPERATURE'
            },
            'max_context_lookback': {
                'type': 'int',
                'min': 5,
                'max': 100,
                'description': 'Number of messages to include in context',
                'env_var': 'MAX_CONTEXT_LOOKBACK'
            },
            'max_room_history': {
                'type': 'int',
                'min': 10,
                'max': 500,
                'description': 'Maximum messages to store per room',
                'env_var': 'MAX_ROOM_HISTORY'
            },
            'llm_timeout': {
                'type': 'int',
                'min': 10,
                'max': 120,
                'description': 'LLM response timeout in seconds',
                'env_var': 'LLM_TIMEOUT'
            },
            'search_timeout': {
                'type': 'int',
                'min': 5,
                'max': 60,
                'description': 'Web search timeout in seconds',
                'env_var': 'SEARCH_TIMEOUT'
            },
            'url_fetch_timeout': {
                'type': 'int',
                'min': 5,
                'max': 60,
                'description': 'URL fetch timeout in seconds',
                'env_var': 'URL_FETCH_TIMEOUT'
            },
            'price_cache_ttl': {
                'type': 'int',
                'min': 60,
                'max': 3600,
                'description': 'Price data cache TTL in seconds',
                'env_var': 'PRICE_CACHE_TTL'
            },
            'enable_meme_generation': {
                'type': 'bool',
                'description': 'Enable/disable meme generation feature',
                'env_var': 'ENABLE_MEME_GENERATION'
            },
            'enable_price_tracking': {
                'type': 'bool',
                'description': 'Enable/disable price tracking feature',
                'env_var': 'ENABLE_PRICE_TRACKING'
            },
            'enable_auto_invite': {
                'type': 'bool',
                'description': 'Enable/disable auto-accepting room invites (Matrix only)',
                'env_var': 'ENABLE_AUTO_INVITE'
            },
            'max_retries': {
                'type': 'int',
                'min': 1,
                'max': 10,
                'description': 'Maximum retry attempts for failed operations',
                'env_var': 'MAX_RETRIES'
            },
            'base_retry_delay': {
                'type': 'int',
                'min': 1,
                'max': 10,
                'description': 'Base delay between retries in seconds',
                'env_var': 'BASE_RETRY_DELAY'
            }
        }
        
        # Load persisted settings if available
        self.runtime_settings = self.load_settings()
        
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file if persistence is enabled"""
        if not self.persistence_enabled or not os.path.exists(self.settings_file):
            return {}
            
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                logger.info(f"Loaded {len(settings)} persisted settings from {self.settings_file}")
                return settings
        except Exception as e:
            logger.error(f"Error loading settings file: {e}")
            return {}
            
    def save_settings(self):
        """Save current settings to file if persistence is enabled"""
        if not self.persistence_enabled:
            return
            
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.runtime_settings, f, indent=2)
                logger.info(f"Saved {len(self.runtime_settings)} settings to {self.settings_file}")
        except Exception as e:
            logger.error(f"Error saving settings file: {e}")
            
    def is_authorized(self, user_id: str, platform: str) -> bool:
        """Check if a user is authorized to manage settings"""
        if platform not in self.authorized_users:
            return False
            
        authorized_list = self.authorized_users[platform]
        if not authorized_list:
            return False
            
        # Clean up the user_id and authorized list for comparison
        user_id = str(user_id).strip()
        authorized_list = [str(u).strip() for u in authorized_list if u]
        
        return user_id in authorized_list
        
    def get_setting_value(self, setting_name: str) -> Any:
        """Get the current value of a setting"""
        # Check runtime settings first
        if setting_name in self.runtime_settings:
            return self.runtime_settings[setting_name]
            
        # Fall back to environment variable
        if setting_name in self.configurable_settings:
            env_var = self.configurable_settings[setting_name]['env_var']
            env_value = os.getenv(env_var)
            
            if env_value is not None:
                setting_type = self.configurable_settings[setting_name]['type']
                if setting_type == 'int':
                    return int(env_value)
                elif setting_type == 'float':
                    return float(env_value)
                elif setting_type == 'bool':
                    return env_value.lower() == 'true'
                else:
                    return env_value
                    
        return None
        
    def update_setting(self, setting_name: str, value: Any) -> tuple[bool, str]:
        """Update a setting value"""
        if setting_name not in self.configurable_settings:
            return False, f"Unknown setting: {setting_name}"
            
        config = self.configurable_settings[setting_name]
        setting_type = config['type']
        
        # Validate and convert value
        try:
            if setting_type == 'int':
                value = int(value)
                if 'min' in config and value < config['min']:
                    return False, f"Value must be at least {config['min']}"
                if 'max' in config and value > config['max']:
                    return False, f"Value must be at most {config['max']}"
                    
            elif setting_type == 'float':
                value = float(value)
                if 'min' in config and value < config['min']:
                    return False, f"Value must be at least {config['min']}"
                if 'max' in config and value > config['max']:
                    return False, f"Value must be at most {config['max']}"
                    
            elif setting_type == 'bool':
                if isinstance(value, str):
                    value = value.lower() in ['true', '1', 'yes', 'on', 'enabled']
                else:
                    value = bool(value)
                    
        except (ValueError, TypeError) as e:
            return False, f"Invalid value type: expected {setting_type}"
            
        # Update runtime setting
        self.runtime_settings[setting_name] = value
        
        # Also update the environment variable for immediate effect
        os.environ[config['env_var']] = str(value)
        
        # Save to file if persistence is enabled
        self.save_settings()
        
        return True, f"Setting '{setting_name}' updated to: {value}"
        
    async def handle_setting_command(self, args: List[str], user_id: str, platform: str) -> str:
        """Handle setting command from users"""
        
        # Check if settings management is enabled
        if not self.persistence_enabled:
            return "⚠️ Settings management is currently disabled."
            
        # Check authorization
        if not self.is_authorized(user_id, platform):
            return "❌ You are not authorized to manage settings."
            
        # Parse command
        if not args or args[0] == 'help':
            return self.get_help_text()
            
        if args[0] == 'list':
            return self.get_settings_list()
            
        if len(args) < 2:
            return "❌ Invalid syntax. Use: `?setting <name> <value>` or `?setting help`"
            
        setting_name = args[0]
        value = ' '.join(args[1:])
        
        # Update the setting
        success, message = self.update_setting(setting_name, value)
        
        if success:
            return f"✅ {message}"
        else:
            return f"❌ {message}"
            
    def get_help_text(self) -> str:
        """Get help text for settings management"""
        help_text = """**⚙️ Settings Management Help**

**Available Commands:**
• `?setting help` - Show this help message
• `?setting list` - Display all configurable settings and their current values
• `?setting <name> <value>` - Update a setting

**Configurable Settings:**
"""
        
        for name, config in self.configurable_settings.items():
            current_value = self.get_setting_value(name)
            help_text += f"\n• **{name}** - {config['description']}"
            
            if config['type'] in ['int', 'float']:
                if 'min' in config and 'max' in config:
                    help_text += f"\n  Range: {config['min']} to {config['max']}"
            elif config['type'] == 'bool':
                help_text += f"\n  Values: true/false"
                
            if current_value is not None:
                help_text += f"\n  Current: `{current_value}`"
                
        help_text += "\n\n**Note:** Only authorized users can manage settings."
        
        return help_text
        
    def get_settings_list(self) -> str:
        """Get a formatted list of all settings and their values"""
        settings_text = "**⚙️ Current Settings**\n\n"
        
        for name, config in self.configurable_settings.items():
            value = self.get_setting_value(name)
            if value is not None:
                settings_text += f"• **{name}**: `{value}`\n"
                settings_text += f"  _{config['description']}_\n"
            else:
                settings_text += f"• **{name}**: _not set_\n"
                settings_text += f"  _{config['description']}_\n"
                
        # Add runtime-only settings that might have been loaded from file
        for name, value in self.runtime_settings.items():
            if name not in self.configurable_settings:
                settings_text += f"• **{name}**: `{value}` _(custom setting)_\n"
                
        return settings_text

# Create singleton instance
settings_manager = SettingsManager()
