import datetime
import os
import sys
import uuid
import json

from bottle import route, run, template, request

import wallet


@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}


@route("/", method="POST")
def process_request():

    begin = datetime.datetime.now()

    data = request.body.read()

    ret = None
    with wallet.Wallet() as w:
        print(f"trying to execute trustlet {int(os.environ['TRUSTLET'])} with {len(data)} output size.")
        trustlet = wallet.Trustlet(int(os.environ['TRUSTLET']))
        output_len = 103000 # 102067 for 503
        ret = trustlet.invoke_trustlet(data, output_len)
        print(f"trustlet returned: {ret}") # todo: remove!
        ret = json.loads(ret)

    end = datetime.datetime.now()

    # memory.close()

    return {
        "begin": begin.strftime("%s.%f"),
        "end": end.strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": None}, # todo: temp
    }


run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
