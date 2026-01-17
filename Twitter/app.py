from dotenv import load_dotenv
import os
import requests
import re
import json 

class TwitterClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('TWEET_SCOUT_API_KEY')
        if not self.api_key:
            raise ValueError("API key is not set. Please make sure TWEET_SCOUT_API_KEY is in your environment variables.")

    def get_user_id(self, user_handle):
        """Fetch Twitter user ID from handle."""
        url = f"https://api.tweetscout.io/v2/handle-to-id/{user_handle}"
        headers = {"Accept": "application/json", "ApiKey": self.api_key}

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('id')
        else:
            print(f"Failed to fetch user ID for @{user_handle}. Status: {response.status_code}")
            return None

    def get_latest_tweets(self, user_handle, user_id, count=5):
        """Fetch the latest `count` tweets from a given user."""
        print('getting latest tweets of user:', str(user_handle) + ' with user_id:', str(user_id))
        url = "https://api.tweetscout.io/v2/user-tweets"
        headers = {
            "Accept": "application/json",
            "ApiKey": self.api_key,
            "Content-Type": "application/json"
        }
        data = {"link": f"https://twitter.com/{user_handle}", "user_id": user_id}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            tweets = response.json()
            tweets = tweets.get('tweets', [])
            # print('got number of tweets:', str(len(tweets)))
            tweet_text = [tweet.get('full_text', '') for tweet in tweets]
            print(f"Successfully fetched {len(tweet_text)} tweets for @{user_handle}.")
            return tweet_text
        else:
            print(f"Failed to fetch tweets for @{user_handle}. Status: {response.status_code}")
            return []

    def extract_sol_contracts(self, tweets):
        """Extract valid Solana contract addresses from tweets."""
        contract_pattern = re.compile(r"\b[A-HJ-NP-Za-km-z1-9]{32,44}\b")  # Matches Solana contract addresses
        contracts = []

        for tweet in tweets:
            matches = contract_pattern.findall(tweet)
            contracts.extend(matches)
        print('found number of contracts:', str(len(contracts)))

        return contracts
