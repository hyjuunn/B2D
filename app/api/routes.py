from fastapi import APIRouter, HTTPException
from app.websocket.binance_client import BinanceWebsocketClient
from app.services.discord_notifier import DiscordNotifier
from binance.client import Client
from app.core.config import settings
from datetime import datetime, timezone
import time

router = APIRouter()

@router.get(
    "/status",
    summary="Get the current status of the WebSocket connection and services",
    tags=["BINANCE INFO"],
    response_model=dict,
)
async def get_status():
    """
    Get the current status of the WebSocket connection and services
    """
    return {
        "status": "running",
        "websocket_connected": BinanceWebsocketClient._ws is not None,
        "listen_key": BinanceWebsocketClient._listen_key is not None,
        "is_running": BinanceWebsocketClient._running
    }

@router.get(
    "/trades/balance",
    summary="Get the current balance of the account",
    tags=["BINANCE INFO"],
    response_model=dict,
)
async def get_balance():
    """
    Get the current balance of the account
    """
    client = Client(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client.futures_account().get('totalWalletBalance')

@router.get(
        "/trades/account",
        summary="Get the current account information",
        tags=["BINANCE INFO"],
        response_model=dict,
)
async def get_account():
    """
    Get the current account information
    """
    client = Client(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
    return client.futures_account()

@router.get(
    "/trades/latest",
    summary="Get today's trades and position information directly from Binance",
    tags=["BINANCE INFO"],
    response_model=dict,
)
async def get_latest_trades():
    """
    Get today's trades and position information directly from Binance
    """
    # TODO: Implement this
    return {"message": "Not implemented"}