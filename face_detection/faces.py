#!/usr/bin/env python

# Copyright 2015 Google, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Draws squares around faces in the given image."""

import argparse
import base64
import os
import time
import random
import requests
import sys
import traceback
from requests.auth import HTTPBasicAuth
from picamera import PiCamera
from time import sleep

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from PIL import Image
from PIL import ImageDraw

from TwitterAPI import TwitterAPI


CONSUMER_KEY = 'gztUP9Qzq6wYNdkp74Mvx1jXX'
CONSUMER_SECRET = 'myPrTBMfl7fxrwi43tceuJrqNNKlURvEOh5NLhtNsB2Rh34Rvg'
ACCESS_TOKEN_KEY = '3366068657-xrnljoddBdU0aAfNxm7zpawByrzRzaw7SUcsXem'
ACCESS_TOKEN_SECRET = 'SBWefFsjZTqmLoSyQd7Hcr6ib4HgPT6kdJ2cdEq6vLMJi'

api = TwitterAPI(CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET)

id = 0
buildKey = 'ZIP-ZIP'
o = None

def build(key):
    url = "https://drukwerkdeal.atlassian.net/builds/rest/api/latest/queue/" + key
    myResponse = requests.post(
        url,
        auth = HTTPBasicAuth('dmyroshnychenko', 'dmyroshnychenko_jira'),
        headers = {'accept': 'application/json', 'Content-Type': 'application/json'},
        data='{}'
    ).json()
    print('Build started')
    return myResponse['buildNumber']

def checkState(key):
    global id
    
    if id:
        url = 'https://drukwerkdeal.atlassian.net/builds/rest/api/latest/result/' + key + '-' + str(id)
        #print(url)
        latest = requests.get(
            url,
            auth = HTTPBasicAuth('dmyroshnychenko', 'dmyroshnychenko_jira'),
            headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
        ).json()
        buildUrl = ''
    else:
        url = 'https://drukwerkdeal.atlassian.net/builds/rest/api/latest/result/' + key
        #print(url)
        myResponse = requests.get(
            url,
            auth = HTTPBasicAuth('dmyroshnychenko', 'dmyroshnychenko_jira'),
            headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
        ).json()

        latest = myResponse['results']['result'][0]

    #for key in latest:
    #    print(key + " : " + str(latest[key]))
    #print(latest['buildState'])
    #print(latest['buildNumber'])

    if latest['lifeCycleState'] == 'Finished':
        id = 0
    
    

# [START get_vision_service]
def get_vision_service():
    credentials = GoogleCredentials.get_application_default()
    return discovery.build('vision', 'v1', credentials=credentials)
# [END get_vision_service]


def detect_face(face_file, max_results=4):
    """Uses the Vision API to detect faces in the given file.

    Args:
        face_file: A file-like object containing an image with faces.

    Returns:
        An array of dicts with information about the faces in the picture.
    """
    image_content = face_file.read()
    batch_request = [{
        'image': {
            'content': base64.b64encode(image_content).decode('utf-8')
            },
        'features': [{
            'type': 'FACE_DETECTION',
            'maxResults': max_results,
            }]
        }]

    service = get_vision_service()
    request = service.images().annotate(body={
        'requests': batch_request,
        })
    response = request.execute()

    face = response['responses'][0]['faceAnnotations']

    print('Joy: {}'.format(face[0]['joyLikelihood']))
    print('Sorrow: {}'.format(face[0]['sorrowLikelihood']))
    print('Angry: {}'.format(face[0]['angerLikelihood']))
    print('Surprise: {}'.format(face[0]['surpriseLikelihood']))

    return face[0]


def highlight_faces(image, face, output_filename, camera):
    """Draws a polygon around the faces, then saves to output_filename.

    Args:
      image: a file containing the image with the faces.
      faces: a list of faces found in the file. This should be in the format
          returned by the Vision API.
      output_filename: the name of the image file to be created, where the
          faces have polygons drawn around them.
    """
    im = Image.open(image)
    draw = ImageDraw.Draw(im)


    box = [(v.get('x', 0.0), v.get('y', 0.0))
           for v in face['fdBoundingPoly']['vertices']]
    draw.line(box + [box[0]], width=5, fill='#00ff00')

    im.save(output_filename)

    #show_build_message(camera, output_filename)
    #sleep(1)
    #remove_o(camera)

def is_happy(face):
     if face['joyLikelihood'] == 'LIKELY':
          return True
     if face['joyLikelihood'] == 'VERY_LIKELY':
          return True
     return False

def is_sad(face):
    if face['sorrowLikelihood'] == 'LIKELY':
        return True
    if face['sorrowLikelihood'] == 'VERY_LIKELY':
        return True
    if face['sorrowLikelihood'] == 'POSSIBLE':
        return True
    if face['angerLikelihood'] == 'LIKELY':
        return True
    if face['angerLikelihood'] == 'VERY_LIKELY':
        return True
    if face['angerLikelihood'] == 'POSSIBLE':
        return True
    return False

def is_build_started():
     global id
     return id != 0

def show_build_message(camera, fname):
    global o
    # Load the arbitrarily sized image
    img = Image.open(fname)
    # Create an image padded to the required size with
    # mode 'RGB'
    pad = Image.new('RGB', (
        ((img.size[0] + 31) // 32) * 32,
        ((img.size[1] + 15) // 16) * 16,
        ))
    # Paste the original image into the padded one
    pad.paste(img, (0, 0))
    
    # Add the overlay with the padded image as the source,
    # but the original image's dimensions
    o = camera.add_overlay(pad.tobytes(), size=img.size)
    # By default, the overlay is in layer 0, beneath the
    # preview (which defaults to layer 2). Here we make
    # the new overlay semi-transparent, then move it above
    # the preview
    o.alpha = 128
    o.layer = 3

def remove_o(camera):
    global o
    if o != None:
        camera.remove_overlay(o)
        o = None

def send_twitter_message(text):
    try:
        #api.request('statuses/update', {'status': text})
        file = open('out.jpg', 'rb')
        data = file.read()
        r = api.request('statuses/update_with_media',
                       {'status': text},
                       {'media[]': data})
    except Exception:
        traceback.print_exc(file=sys.stdout)
    print('twitter message was sent')
    

def main():
    global buildKey
    global id
    global o
    os.environ['GOOGLE_APPLICATION_CREDENTIALS']='/home/pi/hack9/key.json'

    input_filename='image.jpg'
    output_filename='out.jpg'
    max_results=4
    
    camera = PiCamera()
    camera.resolution = (1368, 768)

    camera.start_preview()
    camera.annotate_text_size = 128
    camera.annotate_text='Initialazing'
    #sleep(5)
   
    while True:
        try:
            checkState(buildKey)

            if is_build_started():
                print('Building...')
                camera.annotate_text='Building...'
                continue
            else:
                print('Ready for build')
                remove_o(camera)
                camera.annotate_text='Ready for build'
            
            camera.capture(input_filename)
            with open(input_filename, 'rb') as image:
                try:
                    face = detect_face(image, max_results)
                    highlight_faces(image, face, output_filename, camera)
                except KeyError:
                    continue

                
                if is_sad(face) and not is_build_started():
                    id = build(buildKey)
                    print('sad build was started')
                    show_build_message(camera, 'nook.png')
                    send_twitter_message('#DWDtest your build with id='+str(id)+' will be reverted')
                elif is_happy(face) and not is_build_started():
                    id = build(buildKey)
                    print('happy build was started')
                    show_build_message(camera, 'ok.png')
                    send_twitter_message('#DWDtest your build with id='+str(id)+' was started successfully')
                   
                image.seek(0)
                
        except KeyboardInterrupt:
            print('kbd')
            break
        except Exception:
            traceback.print_exc(file=sys.stdout)
            camera.stop_preview()
            sys.exit(0)
            break
    print('stop preveiw')
    remove_o(camera)
    camera.stop_preview()
    sys.exit(0)

if __name__ == '__main__':
    main()
