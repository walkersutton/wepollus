from os import environ
import requests
from requests_oauthlib import OAuth1

CONSUMER_KEY = environ.get('CONSUMER_KEY')
CONSUMER_SECRET = environ.get('CONSUMER_SECRET')
ACCESS_KEY = environ.get('ACCESS_KEY')
ACCESS_SECRET = environ.get('ACCESS_SECRET')

def request_poll_suggestions():
    url = 'https://api.twitter.com/2/tweets'
    data = {
        'text': "New Daily Poll\n - favorite replies to select tomorrow's poll question\n - top resps on the most favorited reply will be the poll's choices"
    }
    resp = requests.post(url, json=data, auth=OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET))

    if not resp.status_code in (200, 201):
        raise Exception(resp.status_code, resp.text)

    return resp.json()

if __name__ == '__main__':
    request_poll_suggestions()
