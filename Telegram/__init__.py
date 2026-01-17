import asyncio

from BrothersTrusts.CoinSniper.Telegram.app import TelegramBot


async def _run_bot():
    bot = TelegramBot()
    await bot.start()
    await asyncio.Event().wait()


def run_local():
    asyncio.run(_run_bot())


if __name__ == "__main__":
    run_local()