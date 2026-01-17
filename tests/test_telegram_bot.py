import asyncio
import os
import time


class DummyTelegramClient:
    def __init__(self, *args, **kwargs):
        self.connected = False
        self.sent = []
        self.handlers = []

    def add_event_handler(self, handler, event):
        self.handlers.append((handler, event))

    def is_connected(self):
        return self.connected

    async def start(self):
        self.connected = True

    async def send_message(self, handle, message):
        self.sent.append((handle, message))

    async def run_until_disconnected(self):
        await asyncio.sleep(0)

    async def disconnect(self):
        self.connected = False


def _make_bot(monkeypatch):
    monkeypatch.setenv("API_ID", "123")
    monkeypatch.setenv("API_HASH", "abc")
    monkeypatch.setenv("HELIUS_API_KEY", "helius")

    from BrothersTrusts.CoinSniper.Telegram import app as telegram_app

    monkeypatch.setattr(telegram_app, "TelegramClient", DummyTelegramClient)
    return telegram_app.TelegramBot()


def test_extract_sol_contract(monkeypatch):
    bot = _make_bot(monkeypatch)
    message = "Call: 7xKX9S8P9q9Jq9T8W2t7Z5mX3pQz1Yv4U9nH2aX"
    assert bot.extract_sol_contract(message) == "7xKX9S8P9q9Jq9T8W2t7Z5mX3pQz1Yv4U9nH2aX"


def test_extract_token_price(monkeypatch):
    bot = _make_bot(monkeypatch)
    assert bot.extract_token_price("Price $0.000123") == 0.000123
    assert bot.extract_token_price("Entry $1.23") == 1.23
    assert bot.extract_token_price("No price here") is None


def test_query_price_handles_error(monkeypatch):
    bot = _make_bot(monkeypatch)
    monkeypatch.setattr(bot, "_fetch_price_sync", lambda contract: (_ for _ in ()).throw(RuntimeError("boom")))
    price = asyncio.run(bot.query_price("contract"))
    assert price == 0.0


def test_take_profit_sell(monkeypatch):
    bot = _make_bot(monkeypatch)
    async def _send_message(handle, message):
        return None
    bot.send_message = _send_message
    contract = "7xKX9S8P9q9Jq9T8W2t7Z5mX3pQz1Yv4U9nH2aX"
    bot.trades[contract] = {
        "entry": 1.0,
        "high": 2.0,
        "sold": 0.0,
        "opened_at": time.time(),
        "last_price": 2.0,
    }

    async def _run():
        await bot.evaluate_sell(contract, 2.0)

    asyncio.run(_run())
    assert bot.trades[contract]["sold"] == 0.3


def test_trailing_stop_sell(monkeypatch):
    bot = _make_bot(monkeypatch)
    async def _send_message(handle, message):
        return None
    bot.send_message = _send_message
    contract = "7xKX9S8P9q9Jq9T8W2t7Z5mX3pQz1Yv4U9nH2aX"
    bot.trades[contract] = {
        "entry": 1.0,
        "high": 4.0,
        "sold": 0.6,
        "opened_at": time.time(),
        "last_price": 3.0,
    }

    async def _run():
        await bot.evaluate_sell(contract, 2.8)

    asyncio.run(_run())
    assert bot.trades[contract]["sold"] == 1.0


def test_hard_stop_sell(monkeypatch):
    bot = _make_bot(monkeypatch)
    async def _send_message(handle, message):
        return None
    bot.send_message = _send_message
    contract = "7xKX9S8P9q9Jq9T8W2t7Z5mX3pQz1Yv4U9nH2aX"
    bot.trades[contract] = {
        "entry": 1.0,
        "high": 1.0,
        "sold": 0.0,
        "opened_at": time.time(),
        "last_price": 0.6,
    }

    async def _run():
        await bot.evaluate_sell(contract, 0.6)

    asyncio.run(_run())
    assert bot.trades[contract]["sold"] == 1.0


def test_time_based_exit(monkeypatch):
    bot = _make_bot(monkeypatch)
    async def _send_message(handle, message):
        return None
    bot.send_message = _send_message
    contract = "7xKX9S8P9q9Jq9T8W2t7Z5mX3pQz1Yv4U9nH2aX"
    bot.max_hold_seconds = 10
    bot.time_exit_multiplier = 1.2

    opened_at = time.time() - 20
    bot.trades[contract] = {
        "entry": 1.0,
        "high": 1.1,
        "sold": 0.0,
        "opened_at": opened_at,
        "last_price": 1.1,
    }

    async def _run():
        await bot.evaluate_sell(contract, 1.1)

    asyncio.run(_run())
    assert bot.trades[contract]["sold"] == 1.0
