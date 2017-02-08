#!/usr/bin/env python2.7
import numpy as np
import pandas as pd
import warnings
import csv
import cPickle as pickle
import math
import ConfigParser
import json

from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy import spatial
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy import API


def review_to_words(raw_review):
    import re
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        review_text = BeautifulSoup(raw_review, "html.parser").get_text()

        letters_only = re.sub("[^a-zA-Z]", " ", review_text)

        words = letters_only.lower().split()

        stops = pickle.load(open("stopwords.p", "rb"))
        # stops = set(stopwords.words("english"))

        meaningful_words = [w for w in words if not w in stops]

        return " ".join(meaningful_words)


def percentage(nom, denom):
    return 100*float(nom)/float(denom)


def weighting(tfidf, num):
    if tfidf == 0:
        print "Using Top %d by Term Frequency (TF) for vectors" % num
    else:
        print "Using TF-IDF weighting for vectors"
    return


def load (TF):
    if TF == 0:
        t1 = pickle.load(open("t.p", "rb"))
        h1 = pickle.load(open("h.p", "rb"))

    else:
        t1 = pickle.load(open("t_tfidf.p", "rb"))
        h1 = pickle.load(open("h_tfidf.p", "rb"))

    return t1, h1


def classify(tweet):
    ####################################################################################################################
    """ Options
        Toggling the program between GUI and CLI.
        Clearing the text entry box after submission.
        Automation toggle.
        0 for off,  1 for on.
    """
    cosine = 1
    TF_IDF = pickle.load(open("setting_tfidf.p", "rb"))
    # TF_IDF = 1
    features = pickle.load(open("features.p", "rb"))

    ####################################################################################################################
    """ Calculation of vector V
        Loads in V.p representing the processed text for vocabulary generation from the 'Create_vectors' program.
        Vectorizer then counts then creates a vector V to represent the top 5000 words by term frequency.
        This is then fitted to create a term-document matrix.
    """
    clean_train_reviews = pickle.load(open("V.p", "rb"))

    if TF_IDF == 0:
        # Standard bag of words vector based on 'Bag of Words' approach
        vectorizer = CountVectorizer(analyzer="word", tokenizer=None,
                                     preprocessor=None, stop_words=None, max_features=features)
        train_data_features = vectorizer.fit_transform(clean_train_reviews).toarray()

    else:
        # Implement TF-IDF weighting vectorizer
        vectorizer = TfidfVectorizer(min_df=1)
        train_data_features = vectorizer.fit_transform(clean_train_reviews)

    ####################################################################################################################

    """ Vector calculations
        Input vectors calculated and compared against vectors representing authors.
        Output based on the author with the most similarity to the input.
    """
    # Calculation of Input Vector #
    with open('Input.csv', 'wb') as csvfile:  # Creates a .csv file to store the inputted tweet.
        w = csv.writer(csvfile, delimiter="\t", quoting=csv.QUOTE_NONE)
        w.writerow(["Tweet"])

        t = csv.writer(csvfile, delimiter="\t", quoting=csv.QUOTE_ALL)

        input_vec = tweet

        t.writerow([input_vec])  # Writes the inputted tweet to the csv file.

    test_i = pd.read_csv("Input.csv", header=0, delimiter="\t", quoting=3)
    num_reviews = len(test_i["Tweet"])
    clean_test_i = []

    for i in xrange(0, num_reviews):
        clean_input = review_to_words(test_i["Tweet"][i])
        clean_test_i.append(clean_input)

    # Convert the new tweet into a vector after processing.
    if TF_IDF == 0:
        test_input_features = vectorizer.transform(clean_test_i).toarray()
        np.savetxt("Input_vector.csv", test_input_features, delimiter=",")
        new_vec = np.genfromtxt("Input_vector.csv", delimiter=",")

    else:
        train_tf_input = vectorizer.transform(clean_test_i)
        new_vec = np.mean(train_tf_input, axis=0)

    # Classifier of new Tweet #
    trump, hillary = load(TF_IDF)  # Loads author vectors depending on vector weighting required

    if cosine == 1:
        print 'Cosine similarity, bigger is better'
        trump_sim = 1 - spatial.distance.cosine(trump, new_vec)
        hill_sim = 1 - spatial.distance.cosine(hillary, new_vec)
        print 'Trump similarity: ', trump_sim
        print 'Hillary similarity: ', hill_sim
        sum_i = 1

    else:

        print 'TF-IDF similarity, smaller is better'
        sum_i = np.sum(50000*new_vec)  # Multiplication by 50k to ensure vector sum register as non-zero
        sum_h = np.sum(50000*hillary)
        sum_t = np.sum(50000*trump)

        trump_sim = abs(sum_i - sum_t)
        hill_sim = abs(sum_i - sum_h)
        print 'Trump similarity: ', hill_sim
        print 'Hillary similarity: ', trump_sim

    if math.isnan(trump_sim) or sum_i == 0:
        author = 0

    else:
        if trump_sim > hill_sim:
            author = 1

        if hill_sim > trump_sim:
            author = 2

    na = "Error! You aren't like Hillary Clinton or Donald Trump at all!"
    tr = "You tweet like @realDonaldTrump"
    hi = "You tweet like @HillaryClinton"
    if author == 0:
        return na

    if author == 1:
        return tr

    if author == 2:
        return hi

    ####################################################################################################################

config = ConfigParser.ConfigParser()
config.read('.twitter')

consumer_key = config.get('apikey', 'key')
consumer_secret = config.get('apikey', 'secret')
access_token = config.get('token', 'token')
access_token_secret = config.get('token', 'secret')
stream_rule = config.get('app', 'rule')
account_screen_name = config.get('app', 'account_screen_name').lower()
account_user_id = config.get('app', 'account_user_id')

auth = OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
twitterApi = API(auth)


class ReplyToTweet(StreamListener):
    print 'Receiving'
    def on_data(self, data):
        print data
        tweet = json.loads(data.strip())

        retweeted = tweet.get('retweeted')
        from_self = tweet.get('user', {}).get('id_str', '') == account_user_id

        if retweeted is not None and not retweeted and not from_self:

            tweetId = tweet.get('id_str')
            screenName = tweet.get('user', {}).get('screen_name')
            tweetText = tweet.get('text')

            chatResponse = classify(tweetText)
            print chatResponse

            replyText = '@' + screenName + ' ' + chatResponse

            print('Tweet ID: ' + tweetId)
            print('From: ' + screenName)
            print('Tweet Text: ' + tweetText)
            print('Reply Text: ' + replyText)

            # If rate limited, the status posts should be queued up and sent on an interval
            twitterApi.update_status(status=replyText, in_reply_to_status_id=tweetId)

    def on_error(self, status):
        print status


if __name__ == '__main__':
    streamListener = ReplyToTweet()
    twitterStream = Stream(auth, streamListener)
    twitterStream.userstream(_with='user')

