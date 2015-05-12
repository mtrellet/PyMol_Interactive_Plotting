from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin
import json

import argparse
import liblo
import sys
import threading

from OSCHandler.osc_server import MyServer

import logging
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename="flask_session.log", filemode="w", format=FORMAT, level=logging.INFO)

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
        liblo.send( "osc.udp://chm6048.limsi.fr:8000/", "/selected", selected )
        return jsonify(result=wordlist)
    else:
        liblo.send(target, "/selected", False )
        return jsonify(result=wordlist)

def new_plot_callback(path, args):
    logging.info(args)

def fallback(path, args, types, src):
    logging.info("got unknown message '%s' from '%s'" % (path, src.url))
    for a, t in zip(args, types):
        print "argument of type '%s': %s" % (t, a)

def create_osc_server(server_port):
    # create server, listening on port 1234
    try:
        osc_receiver = MyServer(server_port)
        # self.osc_receiver = liblo.Server(self.server_port)
    except liblo.ServerError, err:
        print str(err)
        sys.exit()

    osc_receiver.start()

if __name__ == "__main__":
    # Parse args to setup OSC client
    logging.info("Parsing OSC client params...")
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--client_port", type=int, default=8000,
        help="The port the OSC server is listening on")
    parser.add_argument("--server_ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--server_port", type=int, default=8100,
        help="The port the OSC server is listening on")
    parser.add_argument("--ip", default="0.0.0.0",
        help="The ip of the web server")
    parser.add_argument("--port", type=int, default=5000,
        help="The port the web server is hosted")
    parser.add_argument("--debug", type=bool, default=True,
        help="Debug mode True/False")
    args = parser.parse_args()

    logging.info("Web server \nIP: %s \t PORT: %d \t Debug: %s \nOSC server\nIP: %s \t PORT: %d\n" % (args.ip, args.port, args.debug, args.client_ip, args.client_port))

    # send all messages to port client_port on the local machine
    try:
        target = liblo.Address(args.client_port)
        logging.info("Initialization of sender adress on %s" % target.url)
    except liblo.AddressError, err:
        print str(err)
        sys.exit()

    logging.info(target.url)

    # osc_thread = threading.Thread(target=create_osc_server, args=(args.server_port,))
    # osc_thread.start()

    # osc_client = udp_client.UDPClient(args.osc_ip, args.osc_port)
    app.run(host=args.ip, port=args.port, debug=args.debug)



