#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re, string
import tweepy, time, sys
from tweepy import Stream,API
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
import time #we will use this to limit our consumption
import logging
import warnings
import random
from polyglot.text import Text
from textblob import TextBlob
import json #to capture the tweets

from cfg import topicsdir, ckey, csecret, atoken, asecret, AI_LANG

TOPICS = [f.name.split('.') for f in os.scandir(topicsdir) if f.is_file()]

REPLIES_USERS = []

TOPICS_WORDS = [x[0] for x in TOPICS]

print(TOPICS_WORDS)

# >>> import os
# >>> with os.scandir() as i:
# ...  for entry in i:
# ...   if entry.is_file():
# ...    print(entry.name)
# ...

#evitiamo di retwittare post di alcuni utenti
AVOID_PROFILES = ["Legambiente", "gruppoFIcamera", "forza_italia", "FI_Online_", "FI_Giovani", "LegaNordPadania", "LegaNordMilano", "lega_nord", "matteosalvinimi" ]

#linguaggi supportati

class listener(StreamListener):

    global message

    #pulisce il tweet da hiperlink, testi particolari e caratteri speciali tramite regex
    def clean_tweet(self, tweet):
            '''
            Utility function to clean tweet text by removing links, special characters
            using simple regex statements.
            '''
            #return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())
            return ' '.join(re.sub("(#+)|(@[A-Za-z0-9]+)|(\w+:\/\/\S+)|(RT )", " ", tweet).split())

    def links_remover(self,text):
        link_regex    = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', re.DOTALL)
        links         = re.findall(link_regex, text)
        for link in links:
            text = text.replace(link[0], ', ')
        return text

    def tweet_preprocessor(self,text):
        word_to_esclude_prefixes = ['@','.','?','!']
        word_to_clean = ['#', 'RT', ':)']
        for separator in  string.punctuation:
            if separator not in word_to_esclude_prefixes :
                text = text.replace(separator,' ')
        words = []
        for word in text.split():
            word = word.strip()
            if word:
                if word[0] not in word_to_esclude_prefixes:
                    words.append(word)
                if word[0] in word_to_clean:
                        for x in word_to_clean:
                            words.append(word.replace(x, ''))

        return ' '.join(words)

    def make_logic_reaction(self, sentences, topic, user_feel):
        like = False
        reply = False
        neg = 0
        pos = 0
        message = ""

        print("OK START LOGIC")
        ###############################################

        # DEEP LEVEL OF RESPONSE
        try:
            for idxs, a in enumerate(sentences):
                print("--> Sentence:", a)
                for idxe, b in enumerate(a.entities):
                    print("------> Entity: ", b, "idxe:", idxe)
                    #print("--------------> Neg:", b.negative_sentiment, " Pos:", b.positive_sentiment )
                    print("A", str(topic[0].lower()))
                    if len(b) == 1:
                        print("B", str(b[-1]).lower())

                        if str(topic[0].lower()) in str(b[-1]).lower():
                            pos = b.positive_sentiment
                            neg = b.negative_sentiment
                            print("neg:", neg, " pos:", pos)

                    else:
                        for entities in enumerate(b):
                            print(entities)
        except Exception as e:
            print(e)
            raise e
            #pass

        ##############################################
        print("OK INSIDE LOGIC", pos, neg)
        if pos == 0 and neg == 0 and user_feel == 'a':
            reply = True

        if pos > 0.5 and neg == 0 and user_feel == 'p':
            like = True
            reply = True
        elif pos == 0 and neg < -0.5 and user_feel == 'n':
            like = True
            reply = True

        if reply:
            print("search this file:" + topicsdir + topic)
            with open(topicsdir + topic) as f:

                content = f.readlines()
                # you may also want to remove whitespace characters like `\n` at the end of each line
                content = [x.strip() for x in content]
                message = "@%s %s " % (random.choice(content).encode('utf8'))

        print("End of tweet ------ LIKE:", like, "REPLY:", reply, "MSG:", message)
        return like, reply, message

    def on_data(self, data):
        #while True:

        try:
            all_data = json.loads(data)
            #print(all_data)

        except Exception as e:
            raise e
        #print ("Debug Message: ",all_data)
        try:

            tweetTime = all_data["created_at"]
            #tweet = all_data["text"]
            originaltweet = all_data["text"]
            if all_data["truncated"] == "true":
                originaltweet = all_data["extended_tweet"]["full_text"]
            tweet_in_reply_to_status_id = all_data["in_reply_to_status_id"]
            tweet_in_reply_to_screen_name = all_data["in_reply_to_screen_name"]
            #tweet_mentions_screen_name = all_data["extended_tweet"]["entities"]["user_mentions"]["screen_name"] # []
            #tweet_mentions_name = all_data["extended_tweet"]["entities"]["user_mentions"]["name"] # []
            #tweet_mentions_is = all_data["extended_tweet"]["entities"]["user_mentions"]["id"] # []

            #tweet = self.clean_tweet(originaltweet)

            tweet = self.tweet_preprocessor(self.links_remover(originaltweet))

            #username twitter
            username = all_data["user"]["screen_name"]
            #name twitter
            name = all_data["user"]["name"]
            userid = all_data["user"]["id"]
            userdesc = all_data["user"]["description"]
            user_follower = all_data["user"]["followers_count"]
            user_location = all_data["user"]["location"]
            #user_place = all_data["user"]["place"]
            tweet_id = all_data["id"]
            #linguaggio del tweet
            language = all_data["lang"]
            #cosa abbiamo trovato
            print ("___________________________________________________________________________________________________")
            print ("ORIGINAL: Lang", language, "User:",username, "Follower:", user_follower, "Tweet:", originaltweet)
            print ("MODIFIED: Lang", language, "User:",username, "Follower:", user_follower, "Tweet:", tweet)
        except:
            print ("Unexpected error:", sys.exc_info()[0])
            #pass
            raise

        avoid = False

        for profilo_twitter in AVOID_PROFILES:
            if profilo_twitter in str(tweet.encode('utf8')):
                avoid = True
                pass

        try:

            if avoid:
                print ("Tweet have not passed semanthic filters")
            else:

                reply = False
                retweet = False
                like = False
                avoid = False
                follow = False
                message = False

                pos = 0
                neg = 0


                understood = False

                polytext = Text(str(tweet))

                #TODO: polytext.entities get a cursor with entities[]
                try:
                    print(polytext.pos_tags)
                except Exception as e:
                    pass

            # ADJ: adjective
            # ADP: adposition
            # ADV: adverb
            # AUX: auxiliary verb
            # CONJ: coordinating conjunction
            # DET: determiner
            # INTJ: interjection
            # NOUN: noun
            # NUM: numeral
            # PART: particle
            # PRON: pronoun
            # PROPN: proper noun
            # PUNCT: punctuation
            # SCONJ: subordinating conjunction
            # SYM: symbol
            # VERB: verb
            # X: other

                for idx, topicfound in enumerate(TOPICS):
                    if str(topicfound[0]).lower() in tweet.lower():
                        topic = TOPICS[idx]
                        print("topic=",topic)
                        understood = True

                if understood:
                    # FIRST LEVEL OF RESPONSE
                    try:
                        # punt tweet in polyglot object
                        sentences = polytext.sentences
                        print("BEFOR LOGIC")
                        like, reply, message = self.make_logic_reaction(sentences, topic[0], topic[1])
                        print("AFTER LOGIC")
                    except Exception as e:
                        raise e
                        #pass

                    print ("Processing: REPLY:", reply, " RETWEET:", retweet, " LIKE:", like, " MSG: ", message)
                    if reply:
                        api.update_status(message, in_reply_to_status_id = tweet_id)
                        REPLIES_USERS.append(username)
                        print ("######--> Replyed with:", message)
                    if retweet:
                        api.retweet(tweet_id)
                        print ("######--> Retweet")
                        time.sleep(5)
                    if like:
                        api.create_favorite(tweet_id)
                        print ("######--> Like")
                    if follow:
                        api.create_friendship(username)
                        print ("######--> Follow ", username)

                    #if API.exists_friendship(user_a, user_b):
                    if message:
                        api.send_direct_message(username, "interessante :)")
                    return True
                else:
                    print("Put tis tweet in the trashcan .... ")
                    return True

        except Exception as exx:
            print ("aborted", exx)
            print (sys.exc_info()[0])

            pass
        finally:
            time.sleep(20)

        return True

try:

    #####opening the stream and start listening
    #authorize ourselves using OAuth by just passing the ckey csecret
    auth = OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)
    print("0")
    api = tweepy.API(auth)
    #open the twitter stream by using our class
    # get the user mentions
    mentions = api.mentions_timeline(count=1)
    for mention in mentions:
        print ("Last mention: ", mention.text)
        print (mention.user.screen_name)

    print("1")
    twitterStream = Stream(auth, listener())
    print("2")
    twitterStream.filter(track=[x[0] for x in TOPICS], languages=AI_LANG)
    print("3")
except Exception as ex:
    raise ex
