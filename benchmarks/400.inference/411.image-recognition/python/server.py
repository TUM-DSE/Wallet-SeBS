import datetime
import os
import sys
import uuid
import json
import base64

from function import storage
client = storage.storage.get_instance()

from bottle import route, run, template, request

import wallet


model = None

@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}


@route("/", method="POST")
def process_request():

    begin = datetime.datetime.now()

    data = request.json

    bucket = data.get('bucket').get('bucket')
    input_prefix = data.get('bucket').get('input')
    model_prefix = data.get('bucket').get('model')
    key = data.get('object').get('input')
    model_key = data.get('object').get('model')

    image_download_begin = datetime.datetime.now()
    image = client.download_stream(bucket, os.path.join(input_prefix, key))
    image_download_end = datetime.datetime.now()

    data['image'] = base64.b64encode(image).decode('utf-8')
    del image

    global model
    if not model:
        model = True

        model_download_begin = datetime.datetime.now()
        model_b = client.download_stream(bucket, os.path.join(model_prefix, model_key))
        model_download_end = datetime.datetime.now()

        data['model'] = base64.b64encode(model_b).decode('utf-8')
        del model_b

    data = json.dumps(data)

    ret = None
    with wallet.Wallet() as w:
        print(f"trying to execute trustlet {int(os.environ['TRUSTLET'])} with {len(data)} output size.", file=sys.stderr)
        trustlet = wallet.Trustlet(int(os.environ['TRUSTLET']))
        output_len = 200 # 125 -> 200 for benchmark 411
        ret = trustlet.invoke_trustlet(data, output_len)
        print(f"len: {ret}", file=sys.stderr, flush=True)
        ret = json.loads(ret)

    end = datetime.datetime.now()

    return {
        "begin": begin.strftime("%s.%f"),
        "end": end.strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": ret},
    }


run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
