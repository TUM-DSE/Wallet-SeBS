import datetime
import os
import sys
import uuid

sys.path.append(os.environ['CODE_LOCATION'])
sys.path.append(os.path.join(os.environ['CODE_LOCATION'], '.python_packages/lib/site-packages/'))

import bottle
from bottle import route, run, template, request


@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}


@route("/", method="POST")
def process_request():
    begin = datetime.datetime.now()
    from function import function

    ret = function.handler(request.json)
    end = datetime.datetime.now()

    return {
        "begin": begin.strftime("%s.%f"),
        "end": end.strftime("%s.%f"),
        "request_id": str(uuid.uuid4()),
        "is_cold": False,
        "result": {"output": ret},
    }


run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
