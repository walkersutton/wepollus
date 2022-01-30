from heapq import heapify, heappush, nlargest
from os import environ
from time import sleep
import sys
from tweepy import API, Cursor, OAuthHandler, RateLimitError, TweepError
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys

CONSUMER_KEY = environ.get('CONSUMER_KEY')
CONSUMER_SECRET = environ.get('CONSUMER_SECRET')
ACCESS_KEY = environ.get('ACCESS_KEY')
ACCESS_SECRET = environ.get('ACCESS_SECRET')
WEPOLLUS_USERNAME = 'wepollus'
WEPOLLUS_PASSWORD = environ.get('WEPOLLUS_PASSWORD')
WEPOLLUS_TWITTER_ID = '1248443462883704832'
REPLY_PREFIX_LEN = len("@wepollus ")

auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = API(auth)

def get_poll_question():
    """ returns a Twitter API status object (?) """
    # finding the most recent poll setup status id
    setup_id_str = api.user_timeline(id = WEPOLLUS_TWITTER_ID, count = 1, page = 1)[0].id_str

    # finding the best submitted poll question
    question = None
    questions = Cursor(api.search, q=f'to:{WEPOLLUS_USERNAME}', since_id=setup_id_str, tweet_mode='extended').items()
    while True:
        try:
            question = questions.next()
            if hasattr(question, 'in_reply_to_status_id_str') and question.in_reply_to_status_id == int(setup_id_str):
                if not question or (question.favorite_count > question.favorite_count):
                    reply_count = 0
                    replies = Cursor(api.search, q=f'to:{question.user.screen_name}' , since_id=int(question.id_str), tweet_mode='extended').items()
                    while True:
                        try:
                            # verify that there are at least 2 submitted question choices
                            if (reply_count >= 2):
                                break
                            else:
                                reply = replies.next()
                                if hasattr(reply, 'in_reply_to_status_id_str') and reply.in_reply_to_status_id == int(question.id_str):
                                    reply_count += 1
                        except RateLimitError as e:
                            exit("Twitter api rate limit reached")
                        except TweepError as e:
                            exit("Tweepy error occured")
                        except StopIteration:
                            break
                        except Exception as e:
                            exit("Failed while verifying question reply count")
                    if reply_count >= 2:
                        question.full_text = question.full_text[REPLY_PREFIX_LEN:]
                        question = question
        except RateLimitError as e:
            exit("Twitter api rate limit reached")
        except TweepError as e:
            exit("Tweepy error occured")
        except StopIteration:
            print("stopped iteration")
            break
        except Exception as e:
            exit("Failed while fetching replies")

    # remove the polling tweet if there wasn't enough engagement - eventually will remove for all polling tweets
    if not question:
        api.destroy_status(api.user_timeline(count=1)[0].id)
    return question
    

def get_poll_choices(question):
    """ returns the 4 best poll choices as a list[str] """
    # finding the best choices for the poll
    choices = []
    heapify(choices)
    suggestions = Cursor(api.search, q=f'to:{question.user.screen_name}' , since_id=int(question.id_str), tweet_mode='extended').items()
    while True:
        try:
            choice = suggestions.next()
            if hasattr(choice, 'in_reply_to_status_id_str') and choice.in_reply_to_status_id == int(question.id_str):
                reply_offset = 0
                for user in choice.entities['user_mentions']:
                    reply_offset += (2 + len(user['screen_name']))
                choice_text = choice.full_text[reply_offset:]
                if (len(choice_text) <= 25):
                    heappush(choices, (int(choice.favorite_count), choice_text))
        except RateLimitError as e:
            exit("Twitter api rate limit reached")
        except TweepError as e:
            exit("Tweepy error occured")
        except StopIteration:
            break
        except Exception as e:
            exit("Failed while fetching choices")

    choices = [choice[1] for choice in nlargest(4, choices)]
    return choices

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
            polling_tweet_id = api.user_timeline(count=1)[0].id
            driver.find_element_by_xpath("//*[@name='Tweet']").click()
            api.destroy_status(polling_tweet_id)

    except Exception as e:
        driver.quit()
        exit("generic Selenium exception: " + str(e))

    sleep(2)
    driver.quit()
    sys.exit()



def run_poll():
    poll_question = get_poll_question()

    if poll_question:
        poll_choices = get_poll_choices(poll_question)
        create_poll(poll_question, poll_choices)
    else:
        print('lack of engagement means no poll for today :(')