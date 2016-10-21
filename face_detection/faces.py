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
from requests.auth import HTTPBasicAuth
from picamera import PiCamera
from time import sleep
import easygui

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from PIL import Image
from PIL import ImageDraw

id = 0
buildKey = 'SS-SB'

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


def highlight_faces(image, face, output_filename):
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
     if face['angerLikelihood'] == 'LIKELY':
          return True
     if face['angerLikelihood'] == 'VERY_LIKELY':
          return True
     return False

def is_build_started():
     global id
     return id != 0
     
def main():
    global buildKey
    global id
    os.environ['GOOGLE_APPLICATION_CREDENTIALS']='/home/pi/hack9/key.json'

    input_filename='image.jpg'
    output_filename='out.jpg'
    max_results=4
    
    camera = PiCamera()

    camera.start_preview()
    sleep(5) 
   
    while True:
        checkState(buildKey)
        camera.capture(input_filename)
        with open(input_filename, 'rb') as image:
            if is_build_started():
                print('Building...')
                continue
            else:
                print('Ready for build')
            
            try:
                face = detect_face(image, max_results)
            except KeyError:
                continue
            
            if is_happy(face) and not is_build_started():
                id = build(buildKey)
                print('happy build was started')
                easygui.msgbox('happy build was started', title='success')
            elif is_sad(face) and not is_build_started():
                id = build(buildKey)
                print('sad build was started')
                easygui.msgbox('sad build was started', title='error')
               
            image.seek(0)
            highlight_faces(image, face, output_filename)

    camera.stop_preview()

if __name__ == '__main__':
    main()
