from pydantic_settings import BaseSettings
from typing import Optional
import os
import dotenv

class Settings(BaseSettings):
    dotenv.load_dotenv()
    # Binance API settings
    BINANCE_API_KEY: str
    BINANCE_API_SECRET: str
    
    # OpenAI settings
    OPENAI_API_KEY: str
    
    # Discord Webhook settings
    DISCORD_WEBHOOK_URL: str
    
    # Server settings
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()