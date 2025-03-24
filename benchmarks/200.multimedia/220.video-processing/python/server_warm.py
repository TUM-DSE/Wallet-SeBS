import datetime
import os
import sys
import uuid
import io
import pickle

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
    file = client.download_stream(bucket, os.path.join(input_prefix, key))
    download_stop = datetime.datetime.now()

    data['file'] = file

    data = pickle.dumps(data)

    begin = None
    end = None
    ret = None
    with wallet.Wallet() as w:
        #print(f"trying to execute trustlet {int(os.environ['TRUSTLET'])} with {len(data)} output size.")
        zygote = wallet.Zygote(ZYGOTE_ID)
        trustlet = zygote.create_trustlet(FUNCTION_CODE)
        #trustlet = wallet.Trustlet(int(os.environ['TRUSTLET']))
        output_len = 9328000 # ?????? for benchmark 220
        trustlet.invoke_trustlet_bin("", 0)
        begin = datetime.datetime.now()
        trustlet.invoke_trustlet_bin(data, 0)
        end = datetime.datetime.now()
        ret = trustlet.invoke_trustlet_bin("", output_len)
        ret = pickle.loads(ret)


    upload_begin = datetime.datetime.now()
    filename = os.path.basename(ret['result']['upload_path'])
    upload_key = client.upload_stream(bucket, os.path.join(output_prefix, filename), io.BytesIO(ret['result']['data']))
    upload_stop = datetime.datetime.now()

    ret['result'] = {
        'bucket': bucket,
        'key': upload_key
    }

    return {
        "begin": begin.strftime("%s.%f"),
        "end": (end + (download_stop - download_begin) + (upload_stop - upload_begin)).strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": ret},
    }

ZYGOTE_ID = int(sys.argv[2])
FUNCTION_CODE = sys.argv[3]

run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
