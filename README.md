# CoinSniper

CoinSniper watches selected Twitter accounts for Solana contract addresses and
automates buy/sell execution with a risk-managed exit strategy. It uses:

- `TwitterClient` to fetch tweets and extract Solana contracts.
- `TelegramBot` to place trades via the configured trading bot.
- A sell strategy with take-profits, trailing stop, hard stop, and time-based exit.

## Requirements

- Python 3.10+
- Environment variables:
  - `API_ID`, `API_HASH` (Telegram credentials)
  - `HELIUS_API_KEY` (price queries)
  - `TWEET_SCOUT_API_KEY` (TweetScout API access)

Optional tuning:
- `TWITTER_USERS` (comma-separated handles)
- `BUY_AMOUNT_SOL`
- `PRICE_POLL_SECONDS`
- `MAX_HOLD_SECONDS`
- `TIME_EXIT_MULTIPLIER`
- `TRAILING_START_MULTIPLIER`
- `TRAILING_STOP_FACTOR`
- `HARD_STOP_FACTOR`
- `TWEET_POLL_SECONDS`

## Run

From the repo root:

```
python __init__.py
```

Or provide handles directly:

```
TWITTER_USERS=noe_ether,another_handle python __init__.py
```

If you want to run just the Twitter or Telegram components for local testing:

```
TWITTER_HANDLE=noe_ether python Twitter/__init__.py
python Telegram/__init__.py
```