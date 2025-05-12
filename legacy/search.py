#!/usr/bin/env python
"""Search youtube."""

import os
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
from random import choice
from string import ascii_uppercase


# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = os.environ['DEVELOPER_KEY']
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def youtube_search(options):
    """Search youtube."""
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    search_response = youtube.search().list(
        q=options.q,
        part="id,snippet",
        maxResults=options.max_results
    ).execute()

    # videos = []
    # channels = []
    # playlists = []

    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    for search_result in search_response.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            x = youtube.videos().list(id=search_result["id"]["videoId"], part='statistics').execute()
            # print ("ID: %s, views: %s" % (search_result["id"]["videoId"], x["items"][0]["statistics"]["viewCount"]))
            if int(x["items"][0]["statistics"]["viewCount"]) < 50:
                print ("https://www.youtube.com/watch?v=%s" % (search_result["id"]["videoId"]))
        #    videos.append("%s (%s)" % (search_result["snippet"]["title"], search_result["id"]["videoId"]))
        # elif search_result["id"]["kind"] == "youtube#channel":
        #     channels.append("%s (%s)" % (search_result["snippet"]["title"], search_result["id"]["channelId"]))
        # elif search_result["id"]["kind"] == "youtube#playlist":
        #     playlists.append("%s (%s)" % (search_result["snippet"]["title"], search_result["id"]["playlistId"]))

    # print "Videos:\n", "\n".join(videos), "\n"
    # print "Channels:\n", "\n".join(channels), "\n"
    # print "Playlists:\n", "\n".join(playlists), "\n"


if __name__ == "__main__":
    randstring = (''.join(choice(ascii_uppercase) for i in range(4)))
    # print "searching on: %s" % randstring
    argparser.add_argument("--q", help="Search term", default=randstring)
    argparser.add_argument("--max-results", help="Max results", default=25)
    args = argparser.parse_args()

    try:
        youtube_search(args)
    except HttpError, e:
        print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
