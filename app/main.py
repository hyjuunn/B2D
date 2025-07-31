from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app.core.config import settings
from app.api.routes import router as api_router
from app.websocket.binance_client import BinanceWebsocketClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up the application...")
    await BinanceWebsocketClient.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down the application...")
    await BinanceWebsocketClient.cleanup()

app = FastAPI(
    title="B2D Trading Assistant",
    description="FastAPI server for Binance Futures trading with LLM-powered analysis",
    lifespan=lifespan
)

# Include API routes
app.include_router(api_router, prefix="/api") 