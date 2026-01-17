import asyncio


class DummyTelegramBot:
    def __init__(self):
        self.buys = []

    async def buy_token(self, contract):
        self.buys.append(contract)

    async def start(self):
        return None

    async def close(self):
        return None


class DummyTwitterClient:
    def __init__(self, user_id="123", contracts=None):
        self.user_id = user_id
        self.contracts = contracts or []

    def get_user_id(self, user_handle):
        return self.user_id

    def get_latest_tweets(self, user_handle, user_id, count=5):
        return ["tweet one", "tweet two"]

    def extract_sol_contracts(self, tweets):
        return self.contracts


def test_process_tweets_buys_and_dedupes(monkeypatch):
    from BrothersTrusts.CoinSniper.Controller import app as controller_app

    dummy_bot = DummyTelegramBot()
    dummy_client = DummyTwitterClient(contracts=["abc", "abc", "def"])

    monkeypatch.setattr(controller_app, "TelegramBot", lambda: dummy_bot)
    monkeypatch.setattr(controller_app, "TwitterClient", lambda: dummy_client)

    controller = controller_app.Controller(["user1"])
    asyncio.run(controller.process_tweets())
    asyncio.run(controller.process_tweets())

    assert dummy_bot.buys == ["abc", "def"]


def test_process_tweets_skips_missing_user_id(monkeypatch):
    from BrothersTrusts.CoinSniper.Controller import app as controller_app

    dummy_bot = DummyTelegramBot()
    dummy_client = DummyTwitterClient(user_id=None, contracts=["abc"])

    monkeypatch.setattr(controller_app, "TelegramBot", lambda: dummy_bot)
    monkeypatch.setattr(controller_app, "TwitterClient", lambda: dummy_client)

    controller = controller_app.Controller(["user1"])
    asyncio.run(controller.process_tweets())

    assert dummy_bot.buys == []
