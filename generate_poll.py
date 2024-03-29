from collections import defaultdict
import json
from heapq import heappush, nlargest
from os import environ
import requests
from requests_oauthlib import OAuth1

CONSUMER_KEY = environ.get('CONSUMER_KEY')
CONSUMER_SECRET = environ.get('CONSUMER_SECRET')
ACCESS_KEY = environ.get('ACCESS_KEY')
ACCESS_SECRET = environ.get('ACCESS_SECRET')
BEARER_TOKEN = environ.get('BEARER_TOKEN')
WEPOLLUS_USERNAME = 'wepollus'
WEPOLLUS_PASSWORD = environ.get('WEPOLLUS_PASSWORD')
WEPOLLUS_TWITTER_ID = '1248443462883704832'
REPLY_PREFIX_LEN = len("@wepollus ")
POLL_OPTION_CHARACTER_LIMIT = 25

def bearer_oauth(r):
    r.headers['Authorization'] = f'Bearer {BEARER_TOKEN}'
    return r

def connect_to_endpoint(url, params=None, data=None, type='GET'):
    resp = None
    if type == 'GET':
        resp = requests.get(url, json=data, params=params, auth=bearer_oauth)
    elif type == 'POST':
        resp = requests.post(url, json=data, params=params, auth=OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET))
    elif type == 'DELETE':
        resp = requests.delete(url, json=data, params=params, auth= OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET))

    if not resp.status_code in (200, 201):
        raise Exception(resp.status_code, resp.text)
    return resp.json()

def query_tweet_id():
    url = f'https://api.twitter.com/2/users/{WEPOLLUS_TWITTER_ID}/tweets'
    params = {'max_results': 5}
    resp = connect_to_endpoint(url, params)
    query_tweet_id = None
    for tweet in resp['data']:
        if 'New Daily Poll' in tweet['text']:
            query_tweet_id = tweet['id']
            break
    return query_tweet_id

def delete_tweet(tweet_id):
    url = f'https://api.twitter.com/2/tweets/{tweet_id}'
    # connect_to_endpoint(url, type='DELETE')
    # testing generate tweet

def valid_suggestions():
    ''' Returns a list of valid poll suggestions in descending order of popularity:
    [
        {
            'question': str,
            'options': [
                {
                    'option': str,
                }, ...
            ]
        }, ...
    ]
    '''
    conversation_id = query_tweet_id()
    if not conversation_id:
        return []
    url = 'https://api.twitter.com/2/tweets/search/recent'
    params = {
        'query': f'conversation_id:{conversation_id}',
        'tweet.fields': 'conversation_id,public_metrics,referenced_tweets'
    }
    resp = connect_to_endpoint(url, params)
    conversation_tweets = defaultdict(list)
    if resp['meta']['result_count'] == 0:
        return []
    for tweet in resp['data']:
        conversation_tweets[tweet['referenced_tweets'][0]['id']].append(tweet)

    suggestions = []
    for question_tweet in conversation_tweets[conversation_id]:
        question_text, question_likes = question_tweet['text'][len('@wepollus '):], question_tweet['public_metrics']['like_count']
        options = []
        for option_tweet in conversation_tweets[question_tweet['id']]:
            option_text, option_likes = option_tweet['text'][len('@wepollus '):], option_tweet['public_metrics']['like_count']
            if len(option_text) <= POLL_OPTION_CHARACTER_LIMIT:
                heappush(options, (option_likes, option_text))
        if len(options) >= 2:
            best_options = [option[1] for option in nlargest(4, options)]
            heappush(suggestions, (-1 * question_likes, question_text, best_options))

    delete_tweet(conversation_id)
    return [{'question': suggestion[1], 'options': suggestion[2]} for suggestion in suggestions]

def store_suggestions(suggestions):
    ''' Appends extra suggestions to suggestions.json'''
    if suggestions:
        with open('suggestions.json', 'r+') as f:
            data = json.load(f)
            data['suggestions'].extend(suggestions)
            f.seek(0)
            json.dump(data, f, indent=2)

def pop_suggestion():
    ''' Returns a suggestion from suggestions.json if one exists '''
    suggestion =  None
    with open('suggestions.json', 'r+') as f:
        data = json.load(f)
        if data['suggestions']:
            suggestion = data['suggestions'].pop(0)
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)
    return suggestion

def create_poll(question, options):
    ''' Creates a Twitter poll using the given question and options '''
    url = 'https://api.twitter.com/2/tweets'
    data = {
        'text': f'{question} #poll',
        'poll': {
            'options': options,
            'duration_minutes': 24 * 60
        }
    }
    connect_to_endpoint(url, data=data, type='POST')

if __name__ == '__main__':
    suggestions = valid_suggestions()
    suggestion = None
    if suggestions:
        suggestion, extra_suggestions = suggestions[0], suggestions[1:]
        if extra_suggestions:
            store_suggestions(extra_suggestions)
    else:
        suggestion = pop_suggestion()

    if suggestion:
        create_poll(suggestion['question'], suggestion['options'])
