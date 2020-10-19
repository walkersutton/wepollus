import os
import sys
import tweepy

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_KEY = os.environ.get('ACCESS_KEY')
ACCESS_SECRET = os.environ.get('ACCESS_SECRET')

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

api.update_status("NEW DAILY POLL\n - vote on replies to select tomorrow's question\n - top 2 responses on the most favorited reply will be the poll's options")

sys.exit()
