from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin
import json

import argparse

import liblo

import sys

import logging
logging.basicConfig(filename="flask_session.log", filemode="w", level=logging.INFO)

app = Flask('Visual Analytics')
cors = CORS(app, resources=r'/*', allow_headers='Content-Type')

osc_client = None
target = None


@app.route("/",methods=['GET', 'POST'])
@cross_origin() # allow all origins all methods.
def index():
    return render_template("ajax_test.html")

# @app.route("/json")
# def json(): pass

# From http://stackoverflow.com/questions/23949395/how-to-pass-a-javascript-array-to-a-python-script-using-flask-using-flask-examp
@app.route('/_array2python', methods=['GET', 'POST'])
@cross_origin() # allow all origins all methods.
def array2python():
    global target
    wordlist = json.loads(request.args.get('wordlist'))
    if len(wordlist) > 0:
        selected = [ int(s) for s in wordlist]
        logging.info("Selected models: "+str(selected))
        liblo.send( target, "/selected", selected )
        return jsonify(result=wordlist)
    else:
        liblo.send(target, "/selected", False )

if __name__ == "__main__":
    # Parse args to setup OSC client
    logging.info("Parsing OSC client params...")
    parser = argparse.ArgumentParser()
    parser.add_argument("--osc_ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--osc_port", type=int, default=8000,
        help="The port the OSC server is listening on")
    parser.add_argument("--ip", default="0.0.0.0",
        help="The ip of the web server")
    parser.add_argument("--port", type=int, default=5000,
        help="The port the web server is hosted")
    parser.add_argument("--debug", type=bool, default=True,
        help="Debug mode True/False")
    args = parser.parse_args()

    logging.info("Creating web server and OSC client...")
    logging.info("Web server \nIP: %s \t PORT: %d \t Debug: %s \nOSC server\nIP: %s \t PORT: %d\n" % (args.ip, args.port, args.debug, args.osc_ip, args.osc_port))

    # send all messages to port 1234 on the local machine
    try:
        target = liblo.Address(args.osc_port)
    except liblo.AddressError, err:
        print str(err)
        sys.exit()

    # osc_client = udp_client.UDPClient(args.osc_ip, args.osc_port)
    app.run(host=args.ip, port=args.port, debug=args.debug)

