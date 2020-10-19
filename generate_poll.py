import heapq
import os
import sys
import time
import tweepy
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_KEY = os.environ.get('ACCESS_KEY')
ACCESS_SECRET = os.environ.get('ACCESS_SECRET')
WEPOLLUS_USERNAME = 'wepollus'
WEPOLLUS_PASSWORD = os.environ.get('WEPOLLUS_PASSWORD')
WEPOLLUS_TWITTER_ID = '1248443462883704832'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

# finding the most recent setup status id
setup_id_str = api.user_timeline(id = WEPOLLUS_TWITTER_ID, count = 1, page = 1)[0].id_str

# finding the best submitted poll question
best_question = None
questions = tweepy.Cursor(api.search, q='to:{}'.format(WEPOLLUS_USERNAME), since_id=setup_id_str, tweet_mode='extended').items()
while True:
    try:
        question = questions.next()
        if hasattr(question, 'in_reply_to_status_id_str') and question.in_reply_to_status_id == int(setup_id_str):
            if best_question == None or question.favorite_count > best_question.favorite_count:
                reply_count = 0
                replies = tweepy.Cursor(api.search, q='to:{}'.format(question.user.screen_name) , since_id=int(question.id_str), tweet_mode='extended').items()
                while True:
                    try:
                        # verify that there are at least 2 submitted question choices
                        if (reply_count >= 2):
                            break
                        else:
                            reply = replies.next()
                            if hasattr(reply, 'in_reply_to_status_id_str') and reply.in_reply_to_status_id == int(question.id_str):
                                reply_count += 1
                    except tweepy.RateLimitError as e:
                        exit("Twitter api rate limit reached")
                    except tweepy.TweepError as e:
                        exit("Tweepy error occured")
                    except StopIteration:
                        break
                    except Exception as e:
                        exit("Failed while verifying question reply count")
                if reply_count >= 2:
                    best_question = question
    except tweepy.RateLimitError as e:
        exit("Twitter api rate limit reached")
    except tweepy.TweepError as e:
        exit("Tweepy error occured")
    except StopIteration:
        break
    except Exception as e:
        exit("Failed while fetching replies")

if (best_question == None):
    sys.exit('lack of engagement means no poll for today :(')

# finding the best choices for the poll
choices = []
heapq.heapify(choices)
choices_suggestions = tweepy.Cursor(api.search, q='to:{}'.format(best_question.user.screen_name) , since_id=int(best_question.id_str), tweet_mode='extended').items()
while True:
    try:
        choice = choices_suggestions.next()
        if hasattr(choice, 'in_reply_to_status_id_str') and choice.in_reply_to_status_id == int(best_question.id_str):
            heapq.heappush(choices, (int(choice.favorite_count), choice.full_text))
    except tweepy.RateLimitError as e:
        exit("Twitter api rate limit reached")
    except tweepy.TweepError as e:
        exit("Tweepy error occured")
    except StopIteration:
        break
    except Exception as e:
        exit("Failed while fetching choices")
best_choices = [choice[1] for choice in heapq.nlargest(4, choices)]

# create Twitter poll
opts = Options()
opts.headless = True
driver = webdriver.Firefox(options = opts)
try:
    # login page
    driver.get("https://twitter.com/login")
    time.sleep(2)
    driver.find_element_by_xpath('/html/body/div/div/div/div[2]/main/div/div/div[1]/form/div/div[1]/label/div/div[2]/div/input').send_keys(WEPOLLUS_USERNAME)
    driver.find_element_by_xpath('/html/body/div/div/div/div[2]/main/div/div/div[1]/form/div/div[2]/label/div/div[2]/div/input').send_keys(WEPOLLUS_PASSWORD)
    driver.find_element_by_xpath('/html/body/div/div/div/div[2]/main/div/div/div[1]/form/div/div[3]/div/div').click()

    # select compose tweet
    time.sleep(1)
    driver.find_element_by_xpath('/html/body/div/div/div/div[2]/header/div/div/div/div[1]/div[3]/a/div').click()

    # popualte question
    time.sleep(1)
    driver.find_element_by_xpath('/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[3]/div/div/div/div[1]/div/div/div/div/div[2]/div[1]/div/div/div/div/div/div/div/div/div/div[1]/div/div/div/div[2]/div').send_keys(best_question.full_text)

    # select poll tweet type
    time.sleep(1)
    driver.find_element_by_xpath('/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[3]/div/div/div/div[1]/div/div/div/div/div[2]/div[4]/div/div/div[1]/div[3]/div').click()

    # populate choices
    for ii in range(0, len(best_choices)):
        time.sleep(1)
        if ii > 1:
            # expand choice container
            driver.find_element_by_xpath('/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[3]/div/div/div/div[1]/div/div/div/div/div[2]/div[1]/div/div/div/div/div/div/div/div/div[2]/div/div[1]/div[2]/div/div').click()
        driver.find_element_by_xpath('/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[3]/div/div/div/div[1]/div/div/div/div/div[2]/div[1]/div/div/div/div/div/div/div/div/div[2]/div/div[1]/div[1]/div[' + str(ii + 1) + ']/div/label/div/div[2]/div/input').send_keys(best_choices[ii])

    # tweet!
    driver.find_element_by_xpath('/html/body/div/div/div/div[1]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[3]/div/div/div/div[1]/div/div/div/div/div[2]/div[4]/div/div/div[2]/div[4]').click()

except Exception as e:
    driver.quit()
    exit("generic Selenium exception: " + str(e))

time.sleep(2)
driver.quit()
sys.exit()
