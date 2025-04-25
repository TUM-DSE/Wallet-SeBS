import datetime
import os
import sys
import uuid
import pickle

from bottle import route, run, template, request

import wallet

#sys.path.append("/root/Benchmarks/SeBS/") #For minio

@route("/alive", method="GET")
def alive():
    return {"result:" "ok"}

@route("/stop", method="POST")
def stop_cold():
    global ZYGOTE
    global TRUSTLET
    ZYGOTE = None
    TRUSTLET = None
    return {"result": "ok"}

@route("/cold", method="POST")
def cold_start():
    global ZYGOTE
    global TRUSTLET
    global code_location
    data = request.json
    code_location = data["CODE_LOCATION"]

    for e in ["MINIO_ADDRESS", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"]:
        os.environ[e] = data[e]

    with wallet.Wallet() as w:
        ZYGOTE = w.create_zygote("module/libpal.so",
                                 f"{code_location}/python.manifest",
                                 "module/libsysdb.so")
        TRUSTLET = ZYGOTE.create_trustlet(f"{code_location}/function/function.py")
        os.environ["TRUSTLET"] = str(TRUSTLET.process_id)

    print(f"Created zygote {ZYGOTE} and trustlet {TRUSTLET}")

    sys.path = sys.path[1:]
    sys.path.insert(0, code_location) #storage.py
    with open(f"{code_location}/server.py") as f:
        exec(f.read(),globals())

    print(f"Registered function handler from {code_location}")

    return {"result": "ok"}

if __name__ == "__main__":
    __name__ = "wallet_remote"
    run(host="0.0.0.0", port=int(sys.argv[1]), debug=True)
