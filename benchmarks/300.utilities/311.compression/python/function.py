import datetime
import io
import os
import shutil
import uuid
import base64
import zlib

def parse_directory(directory):

    size = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            size += os.path.getsize(os.path.join(root, file))
    return size

def handler(event):

    download_path = '/tmp/{}-{}'.format(key, uuid.uuid4())
    os.makedirs(download_path)

    s3_download_begin = datetime.datetime.now()
    client.download_directory(bucket, os.path.join(input_prefix, key), download_path)
    s3_download_stop = datetime.datetime.now()
    size = parse_directory(download_path)

    compress_begin = datetime.datetime.now()
    shutil.make_archive(os.path.join(download_path, key), 'zip', root_dir=download_path)
    compress_end = datetime.datetime.now()

    s3_upload_begin = datetime.datetime.now()
    archive_name = '{}.zip'.format(key)
    archive_size = os.path.getsize(os.path.join(download_path, archive_name))
    key_name = client.upload(bucket, os.path.join(output_prefix, archive_name), os.path.join(download_path, archive_name))
    s3_upload_stop = datetime.datetime.now()

    #download_time = (s3_download_stop - s3_download_begin) / datetime.timedelta(microseconds=1)
    #upload_time = (s3_upload_stop - s3_upload_begin) / datetime.timedelta(microseconds=1)
    process_time = (compress_end - compress_begin) / datetime.timedelta(microseconds=1)
    return {
            'result': base64.b64encode(resized).decode('utf-8'),
            'measurement': {
                #'download_time': download_time,
                'download_size': size,
                #'upload_time': upload_time,
                'upload_size': archive_size,
                'compute_time': process_time
            }
        }

