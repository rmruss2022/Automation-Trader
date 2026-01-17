from telethon import TelegramClient, events
import os
import asyncio
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()


class TelegramBot:
    def __init__(self):
        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        self.helius_api_key = os.getenv("HELIUS_API_KEY")

        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH must be set in environment variables.")

        session_name = os.getenv("TELEGRAM_SESSION", "coinsniper_session")
        self.client = TelegramClient(session_name, self.api_id, self.api_hash)
        self.gmgn_bot = os.getenv("GMGN_BOT", "@GMGN_sol04_bot")
        self.dyor_bot = os.getenv("DYOR_BOT", "@TrenchyBot")
        self.buy_amount_sol = os.getenv("BUY_AMOUNT_SOL", "0.00015")

        self.trades = {}
        self.price_poll_seconds = float(os.getenv("PRICE_POLL_SECONDS", "5"))
        self.max_hold_seconds = int(os.getenv("MAX_HOLD_SECONDS", "1800"))
        self.time_exit_multiplier = float(os.getenv("TIME_EXIT_MULTIPLIER", "1.2"))
        self.trailing_start_multiplier = float(os.getenv("TRAILING_START_MULTIPLIER", "2.0"))
        self.trailing_stop_factor = float(os.getenv("TRAILING_STOP_FACTOR", "0.75"))
        self.hard_stop_factor = float(os.getenv("HARD_STOP_FACTOR", "0.7"))
        self.take_profit_levels = [
            (2.0, 0.30),
            (5.0, 0.60),
            (10.0, 0.90),
        ]

        self._monitor_task = None
        self._client_task = None

        self.client.add_event_handler(
            self._handle_gmgn_message, events.NewMessage(from_users=self.gmgn_bot)
        )

    async def start(self):
        if not self.client.is_connected():
            await self.client.start()
        if not self._client_task:
            self._client_task = asyncio.create_task(self.client.run_until_disconnected())
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self.monitor_prices())

    async def close(self):
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        if self._client_task:
            self._client_task.cancel()
            self._client_task = None
        if self.client.is_connected():
            await self.client.disconnect()

    async def send_message(self, handle, message):
        await self.start()
        await self.client.send_message(handle, message)
        print(f"Sent command: {message}")

    async def buy_token(self, contract):
        await self.send_message(self.gmgn_bot, f"/buy {contract} {self.buy_amount_sol}")
        entry_price = await self.query_price(contract)
        if contract not in self.trades:
            self.trades[contract] = {
                "entry": entry_price or 0.0,
                "high": entry_price or 0.0,
                "sold": 0.0,
                "opened_at": time.time(),
                "last_price": entry_price or 0.0,
            }
        print(f"Buy submitted for {contract} at {self.buy_amount_sol} SOL")

    async def sell_token(self, contract, percentage, reason):
        if contract in self.trades and self.trades[contract]["sold"] < 1.0:
            sell_cmd = f"/sell {contract} {percentage}%"
            await self.send_message(self.gmgn_bot, sell_cmd)
            self.trades[contract]["sold"] += percentage / 100
            self.trades[contract]["sold"] = min(self.trades[contract]["sold"], 1.0)
            print(f"Sold {percentage}% of {contract} | Reason: {reason}")

    def extract_sol_contract(self, msg):
        contract_pattern = re.compile(r"\b[A-HJ-NP-Za-km-z1-9]{32,44}\b")
        contracts = contract_pattern.findall(msg)
        return contracts[0] if contracts else None

    def extract_token_price(self, message):
        price_patterns = [
            r"(?:Price|Entry)[^$]*\$(\d+(?:\.\d+)?)",
            r"\$(0\.\d+)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    def _fetch_price_sync(self, contract):
        if not self.helius_api_key:
            return 0.0
        response = requests.post(
            f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "jsonrpc": "2.0",
                "id": "price",
                "method": "getAsset",
                "params": {"id": contract},
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        price = (
            data.get("result", {})
            .get("token_info", {})
            .get("price_info", {})
            .get("price_per_token")
        )
        return float(price) if price else 0.0

    async def query_price(self, contract):
        try:
            return await asyncio.to_thread(self._fetch_price_sync, contract)
        except Exception as exc:
            print(f"Failed to fetch price for {contract}: {exc}")
            return 0.0

    async def _handle_gmgn_message(self, event):
        message = event.message.text or ""
        contract = self.extract_sol_contract(message)
        entry_price = self.extract_token_price(message)

        if contract and entry_price and contract in self.trades:
            trade = self.trades[contract]
            if trade["entry"] == 0.0:
                trade["entry"] = entry_price
                trade["high"] = max(trade["high"], entry_price)
                trade["last_price"] = entry_price
            print(f"Captured entry price {entry_price} for {contract}")

    async def evaluate_sell(self, contract, current_price):
        trade = self.trades[contract]
        entry_price = trade["entry"]
        high_price = trade["high"]
        sold = trade["sold"]

        if entry_price <= 0:
            return

        multiplier = current_price / entry_price

        for level_multiplier, target_sold in self.take_profit_levels:
            if multiplier >= level_multiplier and sold < target_sold:
                sell_pct = round((target_sold - sold) * 100)
                if sell_pct > 0:
                    await self.sell_token(contract, sell_pct, f"{level_multiplier}x take profit")
                return

        if multiplier >= self.trailing_start_multiplier:
            if current_price <= high_price * self.trailing_stop_factor and sold < 1.0:
                remaining_pct = round((1.0 - sold) * 100)
                if remaining_pct > 0:
                    await self.sell_token(contract, remaining_pct, "Trailing stop hit")
                return

        if current_price <= entry_price * self.hard_stop_factor and sold < 1.0:
            remaining_pct = round((1.0 - sold) * 100)
            if remaining_pct > 0:
                await self.sell_token(contract, remaining_pct, "Hard stop loss")
            return

        if time.time() - trade["opened_at"] > self.max_hold_seconds and multiplier < self.time_exit_multiplier:
            remaining_pct = round((1.0 - sold) * 100)
            if remaining_pct > 0:
                await self.sell_token(contract, remaining_pct, "Time-based exit")

    async def monitor_prices(self):
        while True:
            for contract in list(self.trades.keys()):
                trade = self.trades.get(contract)
                if not trade or trade["sold"] >= 1.0:
                    continue

                current_price = await self.query_price(contract)
                if current_price <= 0:
                    continue

                if trade["entry"] == 0.0:
                    trade["entry"] = current_price
                    trade["high"] = current_price

                trade["high"] = max(trade["high"], current_price)
                trade["last_price"] = current_price

                await self.evaluate_sell(contract, current_price)

            await asyncio.sleep(self.price_poll_seconds)

