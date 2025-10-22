"""Basic tests for Polymarket Insider."""

import pytest
from datetime import datetime

from src.polymarket_insider.config.settings import Settings
from src.polymarket_insider.detector.suspicious_trade_detector import SuspiciousTradeDetector
from src.polymarket_insider.api.models import Trade, Market, Token


def test_settings_initialization():
    """Test that settings can be initialized."""
    settings = Settings()
    assert settings.min_trade_size_usd == 10000.0
    assert settings.funding_lookback_hours == 24
    assert settings.trade_history_check_days == 30


def test_trade_model_creation():
    """Test that Trade model can be created."""
    trade = Trade(
        maker="0x1234567890123456789012345678901234567890",
        taker="0x0987654321098765432109876543210987654321",
        price=0.5,
        size=100.0,
        side="BUY",
        token_id="token_123",
        timestamp=datetime.now(),
        transaction_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        usd_size=50000.0
    )

    assert trade.side == "BUY"
    assert trade.usd_size == 50000.0
    assert trade.maker.startswith("0x")


def test_suspicious_trade_detector_initialization():
    """Test that SuspiciousTradeDetector can be initialized."""
    detector = SuspiciousTradeDetector()
    assert detector.min_trade_size == 10000.0
    assert detector.funding_lookback_hours == 24
    assert detector.trade_history_check_days == 30


def test_market_model_creation():
    """Test that Market model can be created."""
    tokens = [
        Token(
            token_id="token_yes",
            price=0.6,
            outcome="Yes"
        ),
        Token(
            token_id="token_no",
            price=0.4,
            outcome="No"
        )
    ]

    market = Market(
        question="Will BTC reach $100k by end of 2024?",
        description="Binary options market for BTC price",
        tokens=tokens
    )

    assert len(market.tokens) == 2
    assert market.tokens[0].outcome == "Yes"
    assert "BTC" in market.question