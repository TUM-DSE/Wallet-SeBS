import datetime
import os
import sys
import uuid
import json
import base64
import io

from function import storage
client = storage.storage.get_instance()

from bottle import route, run, template, request

import wallet


@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}


@route("/", method="POST")
def process_request():

    data = request.json

    bucket = data.get('bucket').get('bucket')
    input_prefix = data.get('bucket').get('input')
    output_prefix = data.get('bucket').get('output')
    key = data.get('object').get('key')

    download_begin = datetime.datetime.now()
    f_data = client.download_stream(bucket, os.path.join(input_prefix, key))
    download_end = datetime.datetime.now()

    data['data'] = base64.b64encode(f_data).decode('ascii')

    data = json.dumps(data)

    begin = None
    end = None
    ret = None
    with wallet.Wallet() as w:
        print(f"trying to execute trustlet {int(os.environ['TRUSTLET'])} with {len(data)} output size.")
        trustlet = wallet.Trustlet(int(os.environ['TRUSTLET']))
        output_len = 115343000 # 115342243 -> 115343000 for benchmark 504
        trustlet.invoke_trustlet("", 0)
        begin = datetime.datetime.now()
        trustlet.invoke_trustlet(data, 0)
        end = datetime.datetime.now()
        ret = trustlet.invoke_trustlet("", output_len)
        ret = json.loads(ret)

    upload_begin = datetime.datetime.now()
    key_name = client.upload_stream(bucket, os.path.join(output_prefix, key), io.BytesIO(json.dumps(ret.get('result')).encode()))
    upload_end = datetime.datetime.now()

    ret['result'] = {
        'bucket': bucket,
        'key': key_name
    }

    return {
        "begin": begin.strftime("%s.%f"),
        "end": (end + (download_end - download_begin) + (upload_end - upload_begin)).strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": ret},
    }


run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
