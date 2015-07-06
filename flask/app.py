from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin
from flask.ext.socketio import SocketIO
import json

import argparse
import liblo
import sys
import threading

from OSCHandler.osc_server import MyServer
from gevent import monkey
monkey.patch_all()

import logging
from RDFHandler.RDF_handling_distant import RDF_Handler

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename="flask_session.log", filemode="w", format=FORMAT, level=logging.INFO)

app = Flask('Visual Analytics')
app.debug = True

cors = CORS(app, resources=r'/*', allow_headers='Content-Type')

socketio = SocketIO(app)

osc_client = None
osc_port = None
target = None

rdf_handler=RDF_Handler("http://localhost:8890/sparql", "http://peptide_traj.com", "http://peptide_traj.com/rules", "my", "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")

# address = ('localhost', 6000)
# conn = Client(address)


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

        ######## MULTIPROC #######
        # print conn
        # conn.send(selected)
        # can also send arbitrary objects:
        # conn.send(['a', 2.5, None, int, sum])
        # conn.close()

        ######## LIBLO ##########
        # LIMSI wired connection
        #liblo.send(('chm6048.limsi.fr',8000), "/selected", selected )
        # EDUROAM
        #liblo.send(('client-172-18-36-30.clients.u-psud.fr', 8000), "/selected", selected)
        # USER DEFINED
        # liblo.send((osc_client, osc_port), "/selected", selected)

        liblo.send(target, "/selected", selected)
        return jsonify(result=wordlist)
    else:
        liblo.send(target, "/selected", False )
        return jsonify(result=wordlist)

@socketio.on('connected', namespace='/socketio')
def connected(message):
    print message['data']
    socketio.emit('response', {'data': 'OK'}, namespace='/socketio')


@socketio.on('get', namespace='/socketio')
def get_available_analyses(message):
    global rdf_handler
    print message['data']
    ava_ana = rdf_handler.get_analyses()
    logging.info("Available analyses: %s" % ava_ana)
    socketio.emit('list_ana', {'data': [ana for ana in ava_ana]}, namespace='/socketio')

@socketio.on('create', namespace='/socketio')
def get_plot_values(message):
    global rdf_handler
    print message['data']
    for x_type, y_type in zip(message['data'][0::2], message['data'][1::2]):
        # Create json file with required information
        json_file = rdf_handler.create_JSON(x_type, y_type)
        # Send json file to webserver
        socketio.emit('new_plot', {'data' : json_file}, namespace='/socketio')
        # Get data ids
        ids = rdf_handler.get_ids(x_type, y_type)
        list_ids = [int(id) for id in ids]
        logging.info("List of ids: %s" % list_ids)
        # Send data ids to PyMol
        liblo.send((osc_client, osc_port), "/ids", list_ids)

    #socketio.emit('list_ana', {'data': [ana for ana in ava_ana]}, namespace='/socketio')

# def new_plot_callback(path, args):
#     logging.info(args)
#
# def fallback(path, args, types, src):
#     logging.info("got unknown message '%s' from '%s'" % (path, src.url))
#     for a, t in zip(args, types):
#         print "argument of type '%s': %s" % (t, a)

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
        logging.info(target.url)
    except liblo.AddressError, err:
        print str(err)
        sys.exit()

    osc_client = args.client_ip
    osc_port = args.client_port
    print osc_client, osc_port
    # osc_thread = threading.Thread(target=create_osc_server, args=(args.server_port,))
    # osc_thread.start()

    # osc_client = udp_client.UDPClient(args.osc_ip, args.osc_port)

    #app.run(host=args.ip, port=args.port, debug=args.debug)
    socketio.run(app, host=args.ip, port=args.port)


