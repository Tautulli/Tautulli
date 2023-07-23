#!/usr/bin/env python

import re


class Emoticons:
    POSITIVE = ["*O", "*-*", "*O*", "*o*", "* *",
                ":P", ":D", ":d", ":p",
                ";P", ";D", ";d", ";p",
                ":-)", ";-)", ":=)", ";=)",
                ":<)", ":>)", ";>)", ";=)",
                "=}", ":)", "(:;)",
                "(;", ":}", "{:", ";}",
                "{;:]",
                "[;", ":')", ";')", ":-3",
                "{;", ":]",
                ";-3", ":-x", ";-x", ":-X",
                ";-X", ":-}", ";-=}", ":-]",
                ";-]", ":-.)",
                "^_^", "^-^"]

    NEGATIVE = [":(", ";(", ":'(",
                "=(", "={", "):", ");",
                ")':", ")';", ")=", "}=",
                ";-{{", ";-{", ":-{{", ":-{",
                ":-(", ";-(",
                ":,)", ":'{",
                "[:", ";]"
                ]


class ParseTweet(object):
    # compile once on import
    regexp = {"RT": "^RT", "MT": r"^MT", "ALNUM": r"(@[a-zA-Z0-9_]+)",
              "HASHTAG": r"(#[\w\d]+)", "URL": r"([https://|http://]?[a-zA-Z\d\/]+[\.]+[a-zA-Z\d\/\.]+)",
              "SPACES": r"\s+"}
    regexp = dict((key, re.compile(value)) for key, value in regexp.items())

    def __init__(self, timeline_owner, tweet):
        """ timeline_owner : twitter handle of user account. tweet - 140 chars from feed; object does all computation on construction
            properties:
            RT, MT - boolean
            URLs - list of URL
            Hashtags - list of tags
        """
        self.Owner = timeline_owner
        self.tweet = tweet
        self.UserHandles = ParseTweet.getUserHandles(tweet)
        self.Hashtags = ParseTweet.getHashtags(tweet)
        self.URLs = ParseTweet.getURLs(tweet)
        self.RT = ParseTweet.getAttributeRT(tweet)
        self.MT = ParseTweet.getAttributeMT(tweet)
        self.Emoticon = ParseTweet.getAttributeEmoticon(tweet)

        # additional intelligence
        if (self.RT and len(self.UserHandles) > 0):  # change the owner of tweet?
            self.Owner = self.UserHandles[0]
        return

    def __str__(self):
        """ for display method """
        return "owner %s, urls: %d, hashtags %d, user_handles %d, len_tweet %d, RT = %s, MT = %s" % \
               (self.Owner, len(self.URLs), len(self.Hashtags), len(self.UserHandles), len(self.tweet), self.RT, self.MT)

    @staticmethod
    def getAttributeEmoticon(tweet):
        """ see if tweet is contains any emoticons, +ve, -ve or neutral """
        emoji = list()
        for tok in re.split(ParseTweet.regexp["SPACES"], tweet.strip()):
            if tok in Emoticons.POSITIVE:
                emoji.append(tok)
                continue
            if tok in Emoticons.NEGATIVE:
                emoji.append(tok)
        return emoji

    @staticmethod
    def getAttributeRT(tweet):
        """ see if tweet is a RT """
        return re.search(ParseTweet.regexp["RT"], tweet.strip()) is not None

    @staticmethod
    def getAttributeMT(tweet):
        """ see if tweet is a MT """
        return re.search(ParseTweet.regexp["MT"], tweet.strip()) is not None

    @staticmethod
    def getUserHandles(tweet):
        """ given a tweet we try and extract all user handles in order of occurrence"""
        return re.findall(ParseTweet.regexp["ALNUM"], tweet)

    @staticmethod
    def getHashtags(tweet):
        """ return all hashtags"""
        return re.findall(ParseTweet.regexp["HASHTAG"], tweet)

    @staticmethod
    def getURLs(tweet):
        r""" URL : [http://]?[\w\.?/]+"""
        return re.findall(ParseTweet.regexp["URL"], tweet)
