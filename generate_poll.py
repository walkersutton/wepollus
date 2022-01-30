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

def connect_to_endpoint(url, params):
    response = requests.get(url, auth=bearer_oauth, params=params)
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
            'choices: [
                {
                    'choice': str,
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
        choices = []
        heapify(choices)
        for choice_tweet in conversation_tweets[question_tweet['id']]:
            choice_text, choice_likes = choice_tweet['text'], choice_tweet['public_metrics']['like_count']
            heappush(choices, (choice_likes, choice_text))
        if len(choices) >= 2:
            best_choices = [choice[1] for choice in nlargest(4, choices)]
            heappush(suggestions, (-1 * question_likes, question_text, best_choices))
    
    return [{'question': suggestion[1], 'choices': suggestion[2]} for suggestion in suggestions]

def store_suggestions(suggestions):
    if suggestions:
        with open('suggestions.json', 'r+') as f:
            data = json.load(f)
            data['suggestions'].extend(suggestions)
            f.seek(0)
            json.dump(data, f, indent=2)

def create_poll(question, choices):
    """ crates a Twitter poll using the given quesiton and choices """
    # create Twitter poll
    opts = Options()
    opts.headless = True
    driver = webdriver.Firefox(options = opts)
    try:
        # login page
        driver.get("https://twitter.com/i/flow/login")
        sleep(2)
        driver.find_element_by_xpath("//*[@autocomplete='username']").send_keys(WEPOLLUS_USERNAME)
        driver.find_element_by_xpath("//*[text()='Next']").click()
        sleep(2)
        driver.switch_to.active_element.send_keys(WEPOLLUS_PASSWORD)

        # TODO - clean up Log in button click action
        driver.find_element_by_xpath("//*[text()='Log in']").click()

        # populate question
        sleep(1)
        driver.find_element_by_class_name('public-DraftEditor-content').send_keys(question.full_text + ' #poll')
        # dismiss hashtag dropdown
        sleep(1)
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()

        # select poll tweet type
        sleep(1)
        driver.find_element_by_xpath('/html/body/div/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/div/div[2]/div[1]/div/div/div/div[2]/div[3]/div/div/div[1]/div[3]').click()

        # populate choices
        for ii in range(len(choices)):
            sleep(1)
            if ii > 1:
                # expand choice container
                driver.find_element_by_xpath("//*[@aria-label='Add a choice']").click()
                
            driver.find_element_by_xpath(f"//*[@name='Choice{ii + 1}']").send_keys(choices[ii])

            # tweet!
            # polling_tweet_id = api.user_timeline(count=1)[0].id
            driver.find_element_by_xpath("//*[@name='Tweet']").click()
            # api.destroy_status(polling_tweet_id)

    except Exception as e:
        driver.quit()
        exit("generic Selenium exception: " + str(e))

    sleep(2)
    driver.quit()
    sys.exit()


def run_poll():
    suggestions = valid_suggestions()
    if not suggestions:
        pass
    best_suggestion, perfectly_valid_suggestions_that_unfortunately_did_not_make_the_cut_for_today = suggestions[0], suggestions[1:]
    store_suggestions(perfectly_valid_suggestions_that_unfortunately_did_not_make_the_cut_for_today)


    # if poll_question:
    #     poll_choices = get_poll_choices(poll_question)
    #     create_poll(poll_question, poll_choices)
    # else:
    #     print('lack of engagement means no poll for today :(')