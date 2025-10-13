"""
Configuration file for ArbiterOS-Core demo.

Set your API keys and configuration here.
"""

import os
from typing import Optional


class Config:
    """Configuration class for ArbiterOS-Core."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-KQfQi1KYNmQLlMsqpxiTADz4wuNGomzFNjoxfEW1MlzT5YjY")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://a.fe8.cn/v1")
    
    # Observability Configuration
    JAEGER_ENDPOINT: Optional[str] = os.getenv("JAEGER_ENDPOINT", None)
    ENABLE_OBSERVABILITY: bool = os.getenv("ENABLE_OBSERVABILITY", "true").lower() == "true"
    
    # Redis Configuration (for persistence)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    ENABLE_PERSISTENCE: bool = os.getenv("ENABLE_PERSISTENCE", "false").lower() == "true"
    
    # Demo Configuration
    DEMO_TIMEOUT: int = int(os.getenv("DEMO_TIMEOUT", "60"))
    DEMO_VERBOSE: bool = os.getenv("DEMO_VERBOSE", "true").lower() == "true"
    
    @classmethod
    def get_openai_config(cls) -> dict:
        """Get OpenAI configuration."""
        return {
            "api_key": cls.OPENAI_API_KEY,
            "base_url": cls.OPENAI_BASE_URL
        }
    
    @classmethod
    def get_observability_config(cls) -> dict:
        """Get observability configuration."""
        return {
            "enable_otel": cls.ENABLE_OBSERVABILITY,
            "jaeger_endpoint": cls.JAEGER_ENDPOINT
        }
    
    @classmethod
    def get_persistence_config(cls) -> dict:
        """Get persistence configuration."""
        return {
            "redis_url": cls.REDIS_URL,
            "enable_persistence": cls.ENABLE_PERSISTENCE
        }


# Global configuration instance
config = Config()
