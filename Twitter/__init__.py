import os

from BrothersTrusts.CoinSniper.Twitter.app import TwitterClient


def run_local(user_handle=None):
    handle = user_handle or os.getenv("TWITTER_HANDLE")
    if not handle:
        raise ValueError("Provide user handle via argument or TWITTER_HANDLE env var.")
    client = TwitterClient()
    user_id = client.get_user_id(handle)
    if not user_id:
        raise ValueError(f"Could not fetch user id for @{handle}.")
    tweets = client.get_latest_tweets(handle, user_id)
    contracts = client.extract_sol_contracts(tweets)
    print(f"Found {len(contracts)} contract(s) from @{handle}: {contracts}")


if __name__ == "__main__":
    run_local()