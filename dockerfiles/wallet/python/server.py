import datetime
import os
import sys
import uuid
import mmap
import ctypes
import json

# todo: temp
sys.path.append(os.environ['CODE_LOCATION'])
sys.path.append(os.path.join(os.environ['CODE_LOCATION'], '.python_packages/lib/site-packages/'))

from bottle import route, run, template, request



@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}


@route("/", method="POST")
def process_request():

    begin = datetime.datetime.now()

    data = request.body.read() + b'\x00'

    # function request/parameter
    memory = mmap.mmap(-1, mmap.ALLOCATIONGRANULARITY, access=mmap.ACCESS_WRITE)
    #request.body.readinto(memory)
    memory.write(data)
    request_mem_address = ctypes.addressof(ctypes.c_char.from_buffer(memory))

    # todo: temporary test
    from function import function
    ret = function.handler(data)

    # todo: create trustlet from a zygote with the argument in request_mem_address getting mapped into the trustlet
    # os.environ['ZYGOTE']
    # ret = json.loads(ctypes.string_at(buffer_address)) # todo: same address? overhead?

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
