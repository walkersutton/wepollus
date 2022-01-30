from collections import defaultdict
import json
from heapq import heapify, heappush, nlargest
from os import environ
from time import sleep
import requests
import sys
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys

BEARER_TOKEN = environ.get('BEARER_TOKEN') # need to add to github
WEPOLLUS_USERNAME = 'wepollus'
WEPOLLUS_PASSWORD = environ.get('WEPOLLUS_PASSWORD')
WEPOLLUS_TWITTER_ID = '1248443462883704832'
REPLY_PREFIX_LEN = len("@wepollus ")

def bearer_oauth(r):
    r.headers['Authorization'] = f'Bearer {BEARER_TOKEN}'
    return r

def connect_to_endpoint(url, params, data=None):
    response = requests.get(url, json=data, auth=bearer_oauth, params=params)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()

def last_query_tweet_id():
    url = f'https://api.twitter.com/2/users/{WEPOLLUS_TWITTER_ID}/tweets'
    params = {'max_results': 15}
    resp = connect_to_endpoint(url, params)
    query_tweet_id = None
    for tweet in resp['data']:
        if 'New Daily Poll' in tweet['text']:
            query_tweet_id = tweet['id']
            break
    return query_tweet_id

def valid_suggestions():
    """ Returns a list of valid poll suggestions in descending order of popularity:
    [
        {
            'question': str,
            'options: [
                {
                    'option': str,
                }, ...
            ]
        }, ...
    ]
    """
    conversation_id = last_query_tweet_id()
    url = 'https://api.twitter.com/2/tweets/search/recent'
    params = {
        'query': f'conversation_id:{conversation_id}',
        'tweet.fields': 'conversation_id,public_metrics,referenced_tweets'
    }
    resp = connect_to_endpoint(url, params)
    conversation_tweets = defaultdict(list)
    for tweet in resp['data']:
        conversation_tweets[tweet['referenced_tweets'][0]['id']].append(tweet)

    suggestions = []
    heapify(suggestions)
    for question_tweet in conversation_tweets[conversation_id]:
        question_text, question_likes = question_tweet['text'], question_tweet['public_metrics']['like_count']
        options = []
        heapify(options)
        for option_tweet in conversation_tweets[question_tweet['id']]:
            option_text, option_likes = option_tweet['text'], option_tweet['public_metrics']['like_count']
            heappush(options, (option_likes, option_text))
        if len(options) >= 2:
            best_options = [option[1] for option in nlargest(4, options)]
            heappush(suggestions, (-1 * question_likes, question_text, best_options))
    
    return [{'question': suggestion[1], 'options': suggestion[2]} for suggestion in suggestions]

def store_suggestions(suggestions):
    if suggestions:
        with open('suggestions.json', 'r+') as f:
            data = json.load(f)
            data['suggestions'].extend(suggestions)
            f.seek(0)
            json.dump(data, f, indent=2)

def pop_suggestion_bank():
    """ Returns a suggestion from suggestions.json if one exists """
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
    """ Creates a Twitter poll using the given question and options """
    url = 'https://api.twitter.com/2/tweets'
    data = {
        'text': question,
        'poll': {
            'options': options,
            'duration_minutes': 24 * 60
        }
    }
    resp = connect_to_endpoint(url, None, data)
    print(resp)

def run_poll():
    suggestions = valid_suggestions()
    selected_suggestion = None
    if suggestions:
        selected_suggestion, extra_suggestions = suggestions[0], suggestions[1:]
        if extra_suggestions:
            store_suggestions(extra_suggestions)
    else: # low engagement, try to pull suggestion from storage
        # TODO
        pass

    # if selected_suggestion:
    #     selected_question = selected_suggestion['question']
    #     question_options = selected_suggestion['options']
    #     create_poll(selected_question, question_options)