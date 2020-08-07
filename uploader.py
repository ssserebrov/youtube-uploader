# More information regarding getting tokens: https://maks.live/articles/python/zagruzka-video-na-youtube/

import random
import json
import time
import subprocess
import sys
import os
import threading

import http
import httplib2

import urllib
import urllib.request

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload

from oauth2client.client import AccessTokenCredentials

from django.conf import settings

# Explicitly tell the underlying HTTP transport library not to retry, since we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status codes is raised.
RETRIABLE_STATUS_CODES = (500, 502, 503, 504)

WORKING_DIR = sys.argv[1]

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_CHUNKSIZE = -1
VIDEO_FILE = ''
VIDEO_FILE_PATH = ''
YOUTUBE_VIDEO_TITLE = ''

def get_auth_code():
    """ Get access token for connect to youtube api """
    oauth_url = 'https://accounts.google.com/o/oauth2/token'
    # create post data
    data = dict(
        refresh_token="<PUT YOU DATA HERE>",
        client_id="<PUT YOU DATA HERE>",
        client_secret="<PUT YOU DATA HERE>",
        grant_type='refresh_token',
    )
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    data = urllib.parse.urlencode(data).encode('utf-8')
    # make request and take response
    request = urllib.request.Request(oauth_url, data=data, headers=headers)
    response = urllib.request.urlopen(request)
    # get access_token from response
    response = json.loads(response.read().decode('utf-8'))
    return response['access_token']


def get_authenticated_service():
    """ Create youtube oauth2 connection """
    # make credentials with refresh_token auth
    credentials = AccessTokenCredentials(access_token=get_auth_code(), user_agent='insta-python/1.0')
    # create connection to youtube api
    return build(
        YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, http=credentials.authorize(httplib2.Http()))


def initialize_upload(youtube):
    """ Create youtube upload data """
    # create video meta data
    body = youtube_meta_data()
    # Call the API's videos.insert method to create and upload the video
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()), body=body,
        media_body=MediaFileUpload(VIDEO_FILE_PATH, chunksize=YOUTUBE_CHUNKSIZE, resumable=True))
    # wait for file uploading
    return resumable_upload(insert_request)


def youtube_meta_data():
    return dict(
        snippet=dict(
            title=YOUTUBE_VIDEO_TITLE,
            tags="",
            categoryId="22",
            description="",
        ),
        status=dict(
            privacyStatus="private",
        )
    )


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if 'id' in response:
                return response['id']
        except HttpError as err:
            if err.resp.status in RETRIABLE_STATUS_CODES:
                error = True
            else:
                raise
        except RETRIABLE_EXCEPTIONS:
            error = True

        if error:
            retry += 1
            if retry > MAX_RETRIES:
                raise Exception('Maximum retry are fail')

            sleep_seconds = random.random() * 2 ** retry
            time.sleep(sleep_seconds)


def upload_video():
    try:
        print("Uploading youtube video", YOUTUBE_VIDEO_TITLE)
        # try to upload video
        video_id = initialize_upload(get_authenticated_service())
        # if failed uploading raise error
        if video_id is None:
            raise Exception('Video ID is None')
        print("Uploaded youtube video", video_id)
        print("Deleting file", VIDEO_FILE_PATH)
        os.remove(VIDEO_FILE_PATH)
    except Exception as error:
        raise
    finally:
        print('')

print("Uploading dir", WORKING_DIR)




def run_check():
    global VIDEO_FILE
    global YOUTUBE_VIDEO_TITLE
    global VIDEO_FILE_PATH
    threading.Timer(86400.0, run_check).start()
    for filename in os.listdir(WORKING_DIR):
        if filename.endswith(".mp4"):
            print("Uploading file", filename)
            VIDEO_FILE = filename
            YOUTUBE_VIDEO_TITLE = os.path.splitext(filename)[0]
            VIDEO_FILE_PATH = os.path.join(WORKING_DIR, VIDEO_FILE)
            upload_video()
            continue
        continue

run_check()
