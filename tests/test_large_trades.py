"""Tests for large trade tracking functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.polymarket_insider.api.goldsky_client import GoldskyClient
from src.polymarket_insider.large_trade_monitor import LargeTradeMonitor
from src.polymarket_insider.config.settings import Settings


@pytest.fixture
def mock_goldsky_client():
    """Create a mock GoldskyClient."""
    client = MagicMock(spec=GoldskyClient)
    client.initialize = AsyncMock()
    client.cleanup = AsyncMock()
    client.get_large_recent_trades = AsyncMock()
    client.format_trade_usd = MagicMock()
    return client


@pytest.fixture
def mock_telegram_bot():
    """Create a mock TelegramAlertBot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def sample_trade_event():
    """Create a sample orderFilledEvent."""
    return {
        'id': 'test-id-123',
        'transactionHash': '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        'timestamp': int(datetime.now().timestamp()),
        'maker': '0x1234567890123456789012345678901234567890',
        'taker': '0x0987654321098765432109876543210987654321',
        'makerAssetId': '0xasset1234567890123456789012345678901234567890',
        'takerAssetId': '0xasset0987654321098765432109876543210987654321',
        'makerAmountFilled': '1000000000',  # 1,000 tokens
        'takerAmountFilled': '15000000000',  # $15,000 in base units
        'fee': '75000000'  # $75 fee
    }


@pytest.mark.asyncio
async def test_goldsky_client_initialization():
    """Test that GoldskyClient can be initialized."""
    client = GoldskyClient()
    assert client.orderbook_url is not None
    assert 'orderbook-subgraph' in client.orderbook_url


@pytest.mark.asyncio
async def test_goldsky_client_format_trade_usd():
    """Test that trade USD formatting works correctly."""
    client = GoldskyClient()

    # Test with $10,000
    event = {'takerAmountFilled': '10000000000'}
    usd = client.format_trade_usd(event)
    assert usd == 10000.0

    # Test with $15,000
    event = {'takerAmountFilled': '15000000000'}
    usd = client.format_trade_usd(event)
    assert usd == 15000.0

    # Test with $100
    event = {'takerAmountFilled': '100000000'}
    usd = client.format_trade_usd(event)
    assert usd == 100.0


@pytest.mark.asyncio
async def test_large_trade_monitor_initialization(mock_goldsky_client, mock_telegram_bot):
    """Test that LargeTradeMonitor can be initialized."""
    monitor = LargeTradeMonitor(
        goldsky_client=mock_goldsky_client,
        telegram_bot=mock_telegram_bot
    )

    assert monitor.goldsky_client == mock_goldsky_client
    assert monitor.telegram_bot == mock_telegram_bot
    assert monitor.running is False
    assert len(monitor.processed_tx_hashes) == 0


@pytest.mark.asyncio
async def test_large_trade_monitor_processes_new_trade(
    mock_goldsky_client,
    mock_telegram_bot,
    sample_trade_event
):
    """Test that monitor processes new trades correctly."""
    # Setup mock to return sample trade
    mock_goldsky_client.get_large_recent_trades.return_value = [sample_trade_event]
    mock_goldsky_client.format_trade_usd.return_value = 15000.0

    monitor = LargeTradeMonitor(
        goldsky_client=mock_goldsky_client,
        telegram_bot=mock_telegram_bot
    )

    # Process trades
    await monitor._check_for_large_trades()

    # Verify trade was fetched
    mock_goldsky_client.get_large_recent_trades.assert_called_once()

    # Verify alert was sent
    mock_telegram_bot.send_message.assert_called_once()
    alert_message = mock_telegram_bot.send_message.call_args[0][0]
    assert '15,000.00' in alert_message
    assert 'LARGE TRADE ALERT' in alert_message

    # Verify transaction was marked as processed
    assert sample_trade_event['transactionHash'] in monitor.processed_tx_hashes


@pytest.mark.asyncio
async def test_large_trade_monitor_skips_duplicate_trades(
    mock_goldsky_client,
    mock_telegram_bot,
    sample_trade_event
):
    """Test that monitor skips already processed trades."""
    mock_goldsky_client.get_large_recent_trades.return_value = [sample_trade_event]
    mock_goldsky_client.format_trade_usd.return_value = 15000.0

    monitor = LargeTradeMonitor(
        goldsky_client=mock_goldsky_client,
        telegram_bot=mock_telegram_bot
    )

    # Process trade twice
    await monitor._check_for_large_trades()
    await monitor._check_for_large_trades()

    # Alert should only be sent once
    assert mock_telegram_bot.send_message.call_count == 1


@pytest.mark.asyncio
async def test_settings_configuration():
    """Test that settings are properly configured."""
    settings = Settings()

    # Verify orderbook URL is set
    assert hasattr(settings, 'goldsky_orderbook_url')
    assert 'orderbook-subgraph' in settings.goldsky_orderbook_url

    # Verify trade threshold
    assert settings.min_trade_size_usd == 10000.0

    # Verify polling interval
    assert settings.polling_interval_seconds == 60


def test_trade_usd_conversion():
    """Test USD conversion from base units."""
    # $10,000 in base units (6 decimals)
    base_units = 10000 * 1_000_000
    usd = base_units / 1_000_000
    assert usd == 10000.0

    # $50,500 in base units
    base_units = 50500 * 1_000_000
    usd = base_units / 1_000_000
    assert usd == 50500.0

    # $100.50 in base units
    base_units = int(100.50 * 1_000_000)
    usd = base_units / 1_000_000
    assert usd == 100.50
