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

    # data = data + b'\x00'
    # memory = mmap.mmap(-1, len(data), access=mmap.ACCESS_WRITE)
    # memory.write(data)
    # request_mem_address = ctypes.addressof(ctypes.c_char.from_buffer(memory))

    ret = None
    with wallet.Wallet() as w:
        print(f"trying to execute trustlet {int(os.environ['TRUSTLET'])}")
        trustlet = wallet.Trustlet(int(os.environ['TRUSTLET']))
        ret = trustlet.invoke_trustlet(data, len(data))
        print(f"trustlet returned: {ret}") # todo: remove
        ret = json.loads(ret)

    end = datetime.datetime.now()

    # memory.close()

    return {
        "begin": begin.strftime("%s.%f"),
        "end": end.strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": ret},
    }


run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
