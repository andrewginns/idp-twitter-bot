#!/usr/bin/env python2.7
import pandas as pd
import warnings
import csv
import cPickle as pickle
import ConfigParser
import json
import os

from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy import API

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


def classify(tweet):

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
    new_vec = vectorizer.transform(clean_test_i)
    test_data = svd.transform(new_vec)

    predictions = list(clf.predict(test_data))
    print test_data.shape
    print predictions[0]

    if predictions[0] == 1.0:
        author = 1

    else:
        author = 2

    tr = "You tweet like @realDonaldTrump"
    hi = "You tweet like @HillaryClinton"

    if author == 1:
        return tr

    if author == 2:
        return hi


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

            print '\nTweet Recieved'
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
    """Options"""
    dimensions = 50

    """Checking parameters are valid"""
    path = '%s/%d' % (os.getcwd(), dimensions)
    if os.path.exists(path) is True:
        print '\nDimension folder found'
    else:
        print '\nNo folder found for %d dimensions, please run Create_SVD with required dimensions first' % dimensions
        exit()

    """ Calculation of vector V
        Loads in V.p representing the processed text for vocabulary generation from the 'Create_vectors' program.
        Vectorizer then counts then creates a vector V to represent the top 5000 words by term frequency.
        This is then fitted to create a term-document matrix.
    """

    clean_train_reviews = pickle.load(open("V.p", "rb"))

    # Implement TF-IDF weighting vectorizer
    vectorizer = TfidfVectorizer(min_df=1)
    vectorizer.fit_transform(clean_train_reviews)

    # Classifier of new Tweet #
    """Loading trained SVD"""
    svd = pickle.load(open("%s/svd_trained.p" % path, "rb"))

    """Loading training data"""
    train_data = pickle.load(open("%s/unlabelled_svd_train.p" % path, "rb"))
    print '\nTraining data shape:'
    print train_data.shape

    array_train_labels = pickle.load(open("%s/labels_svd_train.p" % path, "rb"))
    print '\nLabels shape:'
    print array_train_labels.shape
    print '\n Trump Train ID: %d' % array_train_labels[0][0]
    print '\n Hillary Train ID: %d' % array_train_labels[-1][0]
    train_labels = array_train_labels.ravel()

    """Predicting the author"""
    linear_svc = SVC(kernel='linear', C=0.551)
    clf = linear_svc

    clf.fit(train_data, train_labels)
    print '\nAwaiting input:'
    streamListener = ReplyToTweet()
    twitterStream = Stream(auth, streamListener)
    twitterStream.userstream(_with='user')

