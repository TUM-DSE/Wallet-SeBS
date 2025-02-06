#!/usr/bin/env python

import datetime
import os
import subprocess


def call_ffmpeg(args):
    ret = subprocess.run([os.path.join('/dependencies', 'ffmpeg'), '-y'] + args,
            #subprocess might inherit Lambda's input for some reason
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if ret.returncode != 0:
        print('Invocation of ffmpeg failed!')
        print('Out: ', ret.stdout.decode('utf-8'))
        raise RuntimeError()

# https://superuser.com/questions/556029/how-do-i-convert-a-video-to-gif-using-ffmpeg-with-reasonable-quality
def to_gif(video, duration, event):
    output = '/tmp/processed-{}.gif'.format(os.path.basename(video))
    call_ffmpeg(["-i", video,
        "-t",
        "{0}".format(duration),
        "-vf",
        "fps=10,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        output])
    return output

# https://devopstar.com/2019/01/28/serverless-watermark-using-aws-lambda-layers-ffmpeg/
def watermark(video, duration, event):
    output = '/tmp/processed-{}'.format(os.path.basename(video))
    call_ffmpeg([
        "-i", video,
        "-i", os.path.join('/dependencies', 'watermark.png'),
        "-t", "{0}".format(duration),
        "-filter_complex", "overlay=main_w/2-overlay_w/2:main_h/2-overlay_h/2",
        output])
    return output

def transcode_mp3(video, duration, event):
    pass

operations = { 'transcode' : transcode_mp3, 'extract-gif' : to_gif, 'watermark' : watermark }

def handler(event):

    key = event.get('object').get('key')
    duration = event.get('object').get('duration')
    op = event.get('object').get('op')
    download_path = '/tmp/{}'.format(key)
    os.makedirs("/tmp", exist_ok=True)

    with open(download_path, "wb") as f:
        f.write(event.get('file'))

    download_size = os.path.getsize(download_path)

    process_begin = datetime.datetime.now()
    upload_path = operations[op](download_path, duration, event)
    process_end = datetime.datetime.now()

    upload_size = os.path.getsize(upload_path)
    with open(upload_path, "rb") as f:
        result = f.read()

    #download_time = (download_stop - download_begin) / datetime.timedelta(microseconds=1)
    #upload_time = (upload_stop - upload_begin) / datetime.timedelta(microseconds=1)
    process_time = (process_end - process_begin) / datetime.timedelta(microseconds=1)
    return {
            'result': {
                'data': result,
                'upload_path': upload_path
            },
            'measurement': {
                #'download_time': download_time,
                'download_size': download_size,
                #'upload_time': upload_time,
                'upload_size': upload_size,
                'compute_time': process_time
            }
        }

