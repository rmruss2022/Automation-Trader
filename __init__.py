import asyncio
import os

from BrothersTrusts.CoinSniper.Controller.app import Controller


def run_controller_local(twitter_users=None):
    users = twitter_users or os.getenv("TWITTER_USERS", "")
    if isinstance(users, str):
        users = [user.strip() for user in users.split(",") if user.strip()]
    if not users:
        raise ValueError("Provide twitter users via argument or TWITTER_USERS env var.")
    controller = Controller(users)
    asyncio.run(controller.run())


if __name__ == "__main__":
    run_controller_local()
