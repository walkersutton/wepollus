from os import environ
import sys
from tweepy import API, OAuthHandler

CONSUMER_KEY = environ.get('CONSUMER_KEY')
CONSUMER_SECRET = environ.get('CONSUMER_SECRET')
ACCESS_KEY = environ.get('ACCESS_KEY')
ACCESS_SECRET = environ.get('ACCESS_SECRET')

auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = API(auth)

api.update_status("New Daily Poll\n - favorite replies to select tomorrow's poll question\n - top responses on the most favorited reply will be the poll's choices")

sys.exit()
