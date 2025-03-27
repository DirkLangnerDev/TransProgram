import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """
    Configuration manager for the application.
    Handles loading and saving configuration settings, particularly for LLM providers.
    """
    
    DEFAULT_CONFIG = {
        "llm": {
            "provider": "ollama",  # Default to local Ollama
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "gemma3:12b"
            },
            "openai": {
                "api_key": "",
                "model": "gpt-4o"
            },
            "anthropic": {
                "api_key": "",
                "model": "claude-3-opus-20240229"
            }
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses 'config.json' in the current directory.
        """
        self.config_path = Path(config_path or "config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default if it doesn't exist.
        
        Returns:
            The loaded configuration dictionary
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                # Ensure all required sections exist
                for section, defaults in self.DEFAULT_CONFIG.items():
                    if section not in config:
                        config[section] = defaults
                    elif isinstance(defaults, dict):
                        # For nested sections, ensure all default keys exist
                        for key, value in defaults.items():
                            if key not in config[section]:
                                config[section][key] = value
                
                return config
            except Exception as e:
                print(f"Error loading config from {self.config_path}: {e}")
                print("Using default configuration")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            config = self.DEFAULT_CONFIG.copy()
            self._save_config(config)
            return config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.
        
        Args:
            config: The configuration dictionary to save
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config to {self.config_path}: {e}")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get the LLM configuration.
        
        Returns:
            A dictionary with the LLM configuration
        """
        return self.config.get("llm", self.DEFAULT_CONFIG["llm"])
    
    def update_llm_config(self, provider: Optional[str] = None, **kwargs) -> None:
        """
        Update the LLM configuration.
        
        Args:
            provider: The LLM provider to use ('ollama', 'openai', or 'anthropic')
            **kwargs: Additional configuration parameters for the provider
        """
        llm_config = self.config.setdefault("llm", self.DEFAULT_CONFIG["llm"].copy())
        
        if provider:
            llm_config["provider"] = provider
        
        # Update provider-specific configuration
        current_provider = llm_config["provider"]
        provider_config = llm_config.setdefault(current_provider, {})
        
        for key, value in kwargs.items():
            provider_config[key] = value
        
        self._save_config(self.config)
    
    def save(self) -> None:
        """Save the current configuration to file."""
        self._save_config(self.config)

# Example usage:
# config = Config()
# llm_config = config.get_llm_config()
# print(f"Using LLM provider: {llm_config['provider']}")
# 
# # Update configuration
# config.update_llm_config(provider="openai", api_key="your-api-key")
