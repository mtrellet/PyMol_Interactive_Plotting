from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
import json

import argparse
import time

from pythonosc import osc_message_builder
from pythonosc import udp_client


app = Flask(__name__)

@app.route("/",methods=['GET', 'POST'])
def index():
    return render_template("ajax_test.html")

# @app.route("/json")
# def json(): pass

# From http://stackoverflow.com/questions/23949395/how-to-pass-a-javascript-array-to-a-python-script-using-flask-using-flask-examp
@app.route('/_array2python', methods=['GET', 'POST'])
def array2python():
    wordlist = json.loads(request.args.get('wordlist'))
    # do some stuff
    print wordlist
    msg = osc_message_builder.OscMessageBuilder(address = "/filter")
    msg.add_arg(worldlist)
    msg = msg.build()
    client.send(msg)
    # return jsonify(result=wordlist)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--port", type=int, default=8000,
        help="The port the OSC server is listening on")
    args = parser.parse_args()

    client = udp_client.UDPClient(args.ip, args.port)

    app.run(host='0.0.0.0',port=5000,debug=True)
