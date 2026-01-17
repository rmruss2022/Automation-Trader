import asyncio
import os

from BrothersTrusts.CoinSniper.Telegram.app import TelegramBot
from BrothersTrusts.CoinSniper.Twitter.app import TwitterClient


class Controller:
    def __init__(self, twitter_users):
        self.telegram_bot = TelegramBot()
        self.twitter_client = TwitterClient()
        self.twitter_users = twitter_users  # List of Twitter handles
        self.seen_contracts = set()
        self.poll_interval_seconds = int(os.getenv("TWEET_POLL_SECONDS", "120"))

    async def process_tweets(self):
        """Fetch tweets, extract contract addresses, and send them via Telegram."""
        for user_handle in self.twitter_users:
            print(f"Checking tweets from @{user_handle}...")

            user_id = self.twitter_client.get_user_id(user_handle)
            print('user_id:', str(user_id))
            if not user_id:
                print(f"Skipping {user_handle}: Could not fetch user ID.")
                continue

            tweets = self.twitter_client.get_latest_tweets(user_handle, user_id)
            contracts = self.twitter_client.extract_sol_contracts(tweets)
            print('contracts in controller: ' + str(contracts))

            if contracts:
                for contract in contracts:
                    if contract in self.seen_contracts:
                        continue
                    self.seen_contracts.add(contract)
                    await self.telegram_bot.buy_token(contract)
            else:
                print(f"No valid Solana contract addresses found in tweets from @{user_handle}.")

    async def run(self):
        """Start the full process of fetching tweets and sending messages."""
        try:
            await self.telegram_bot.start()
            while True:
                await self.process_tweets()
                await asyncio.sleep(self.poll_interval_seconds)
        except Exception as e:
            print(f"An error occurred: {e}")
            await self.telegram_bot.close()
        await self.telegram_bot.close()

