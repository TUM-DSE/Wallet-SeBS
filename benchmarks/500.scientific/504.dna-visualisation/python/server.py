import datetime
import os
import sys
import uuid
import mmap
import ctypes
import json
import base64
import io

# todo: temp
sys.path.append(os.path.join(os.path.dirname(__file__), '.python_packages/lib/site-packages/'))

from function import storage
client = storage.storage.get_instance()

from bottle import route, run, template, request



@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}


@route("/", method="POST")
def process_request():

    begin = datetime.datetime.now()

    data = request.json

    bucket = data.get('bucket').get('bucket')
    input_prefix = data.get('bucket').get('input')
    output_prefix = data.get('bucket').get('output')
    key = data.get('object').get('key')

    download_begin = datetime.datetime.now()
    f_data = client.download_stream(bucket, os.path.join(input_prefix, key))
    download_stop = datetime.datetime.now()

    data['data'] = base64.b64encode(f_data).decode('utf-8')

    # function request/parameter
    encoded = json.dumps(data).encode('utf-8') + b'\x00'
    memory = mmap.mmap(-1, len(encoded), access=mmap.ACCESS_WRITE)
    memory.write(encoded)
    request_mem_address = ctypes.addressof(ctypes.c_char.from_buffer(memory))

    # todo: temporary test
    from function import function
    ret = function.handler(data)

    # todo: run trustlet with the argument in request_mem_address getting mapped into the trustlet
    # os.environ['TRUSTLET']
    # ret = json.loads(ctypes.string_at(buffer_address)) # todo: same address? overhead?

    upload_begin = datetime.datetime.now()
    buf = io.BytesIO(ret.get('result').encode())
    buf.seek(0)
    key_name = client.upload_stream(bucket, os.path.join(output_prefix, key), buf)
    upload_stop = datetime.datetime.now()
    buf.close()

    ret['result'] = {
        'bucket': bucket,
        'key': key_name
    }

    end = datetime.datetime.now()

    memory.close()

    return {
        "begin": begin.strftime("%s.%f"),
        "end": end.strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": ret},
    }


run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
