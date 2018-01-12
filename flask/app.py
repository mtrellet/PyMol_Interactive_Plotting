from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO
from nocache import nocache
import json

import argparse
import liblo
import sys
import threading
import time

from OSCHandler.osc_server import MyServer


import logging
from RDFHandler.RDF_handling_distant import RDF_Handler

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)s %(funcName)s - %(message)s'
logging.basicConfig(filename="flask_session.log", filemode="w", format=FORMAT, level=logging.DEBUG)

logging.getLogger('flask_cors').level = logging.DEBUG

app = Flask('Visual Analytics')
app.debug = False

cors = CORS(app, resources=r'/*', allow_headers='Content-Type')

socketio = SocketIO(app)

# Arguments and params initialisation
osc_client = None
osc_port = None
target = None
moliscope = False
context = "weak"
# rdf_handler=RDF_Handler(server="http://localhost:8890/sparql", graph="http:// glic_traj_rmsd_nomemb_ligand_0_50_1.com",
#                         rules="http://glic_traj_rmsd_nomemb_ligand_0_50_1.com/rules",
#                         prefix="my", uri="http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
rdf_handler=RDF_Handler(server="http://localhost:8890/sparql", graph="http://peptide_traj.org",
                        rules="http://visuana.org/rules",
                        prefix="my", uri="http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
ids = {'model': [], 'residue':[], 'chain': [], 'atom': []}
hierarchical_lvl = {'model': 4, 'residue':2, 'chain': 3, 'atom': 1}
filter_ids = {'model': [], 'residue':[], 'chain': [], 'atom': []}

# address = ('localhost', 6000)
# conn = Client(address)


@app.route("/",methods=['GET', 'POST'])
@cross_origin() # allow all origins all methods.
@nocache
def index():
    return render_template("ajax_test.html")

# @app.route("/json")
# def json(): pass

# From http://stackoverflow.com/questions/23949395/how-to-pass-a-javascript-array-to-a-python-script-using-flask-using-flask-examp
@app.route('/_array2python', methods=['GET', 'POST'])
@cross_origin() # allow all origins all methods.
@nocache
def array2python():
    logging.warning("app.py = NEW SELECTION")
    idlist = json.loads(request.args.get('idlist'))
    plot_level = str(request.args.get('plot_level'))
    if len(idlist) > 0:
        selected_uniq_ids = [ int(s) for s in idlist]

        # Convert uniq ids from plots to biologically meaningful ids
        logging.info("Selected models (uniq_id): "+str(selected_uniq_ids))
        selected_bio_ids = rdf_handler.from_uniq_to_bio_ids(plot_level, selected_uniq_ids)
        logging.info("Selected models (bio_id): "+str(selected_bio_ids))

        if plot_level != 'model':
            liblo.send((osc_client, osc_port), "/moliscope/hide_level", plot_level)
            hierarchical_tree_for_selection = rdf_handler.from_uniq_to_hierarchical_tree(plot_level, selected_uniq_ids)
            for key in hierarchical_tree_for_selection.iterkeys():
                liblo.send((osc_client, osc_port), "/moliscope/new_submodel_selection", hierarchical_tree_for_selection[key]['model'],
                           hierarchical_tree_for_selection[key]['chain'], hierarchical_tree_for_selection[key]['residue'],
                           hierarchical_tree_for_selection[key]['atom'])
        else:
            if moliscope:
                liblo.send((osc_client, osc_port), "/moliscope/new_selection", *selected_bio_ids)
            else:
                liblo.send((osc_client, osc_port), "/selected", selected_bio_ids)

        logging.info("Selected models sent on: %s:%s" % (osc_client, osc_port))
        ids[plot_level] = selected_bio_ids
        logging.info("Ids stored as selected in app.py: %s" % ids)
        return jsonify(result=True)
    else:
        ids[plot_level] = []
        if moliscope:
            liblo.send((osc_client, osc_port), "/moliscope/new_selection", None )
        else:
            liblo.send((osc_client, osc_port), "/selected", 0 )
        return jsonify(result=idlist)

    ######## LIBLO ##########
    # LIMSI wired connection
    #liblo.send(('chm6048.limsi.fr',8000), "/selected", selected )
    # EDUROAM
    #liblo.send(('client-172-18-36-30.clients.u-psud.fr', 8000), "/selected", selected)
    # USER DEFINED
    # liblo.send((osc_client, osc_port), "/selected", selected)

@app.route('/_uniq_selection', methods=['GET', 'POST'])
@cross_origin() # allow all origins all methods.
@nocache
def uniq_selection():
    logging.warning("app.py = NEW UNIQ SELECTION")
    global rdf_handler
    selected = json.loads(request.args.get('selected'))
    info = rdf_handler.get_info_uniq(selected)
    logging.info("Info: %s" % info)
    # liblo.send(target, "/selected", selected)
    liblo.send((osc_client, osc_port), "/selected", selected)
    logging.info("Selected models sent on: %s:%s" % (osc_client, osc_port))
    return jsonify(result=selected)

@socketio.on('connected', namespace='/socketio')
def connected(message):
    logging.info(message['data'])
    global ids, filter_ids
    ids = {'model': [], 'residue':[], 'chain': [], 'atom': []}
    filter_ids = {'model': [], 'residue':[], 'chain': [], 'atom': []}
    socketio.emit('response', {'data': 'OK'}, namespace='/socketio')


@socketio.on('get', namespace='/socketio')
def get_available_analyses(message):
    global rdf_handler
    logging.info(message['data'])
    ava_ana = rdf_handler.get_analyses()
    logging.info("Available analyses: {}".format(ava_ana))
    socketio.emit('list_model_ana', {'data': [ana for ana in ava_ana['Model']]}, namespace='/socketio')
    socketio.emit('list_chain_ana', {'data': [ana for ana in ava_ana['Chain']]}, namespace='/socketio')
    socketio.emit('list_residue_ana', {'data': [ana for ana in ava_ana['Residue']]}, namespace='/socketio')
    socketio.emit('list_atom_ana', {'data': [ana for ana in ava_ana['Atom']]}, namespace='/socketio')

@socketio.on('create', namespace='/socketio')
def get_plot_values(message):
    logging.warning("app.py = CREATE PLOT")
    global rdf_handler
    logging.info(message)
    filter_nb = 0
    for x_type, y_type in zip(message['data'][0::2], message['data'][1::2]):
        # Create json file with required information
        for lvl in ids.keys(): # Check for higher levels models
            # print lvl, hierarchical_lvl[message['lvl']], hierarchical_lvl[lvl]
            if ids[lvl] and hierarchical_lvl[message['lvl']] < hierarchical_lvl[lvl]:
                filter_ids[lvl] = ids[lvl]
                filter_nb += 1

        if filter_nb > 0:
            logging.info("Filter ids: %s" % filter_ids)
            json_file = rdf_handler.create_JSON(x_type, y_type, message['lvl'], filter_ids)
        else:
            json_file = rdf_handler.create_JSON(x_type, y_type, message['lvl'])
        # Send json file to webserver
        socketio.emit('new_plot', {'data' : json_file, 'lvl': message['lvl']}, namespace='/socketio')
        # Get data ids
        all_ids = rdf_handler.get_ids(x_type, y_type, message['lvl'])
        list_ids = [int(id) for id in all_ids]
        logging.info("List of ids: %s" % list_ids)
        # Send data ids to PyMol
        if moliscope:
            liblo.send((osc_client, osc_port), "/moliscope/set_level", message['lvl'])
            liblo.send((osc_client, osc_port), "/moliscope/ids", list_ids)
        else:
            liblo.send((osc_client, osc_port), "/ids", list_ids)

@socketio.on('update', namespace='/socketio')
def update_plot_values(message):
    logging.warning("app.py = UPDATE PLOT")
    global rdf_handler
    logging.info(message)
    filter_nb = 0
    for plot in message['data']:
        x_type = plot[0]
        y_type = plot[1]
    # for x_type, y_type in zip(message['data'][0::2], message['data'][1::2]):
        # Create json file with required information
        for lvl in ids.keys(): # Check for higher levels models
            # print lvl, hierarchical_lvl[message['lvl']], hierarchical_lvl[lvl]
            if ids[lvl] and hierarchical_lvl[message['lvl']] < hierarchical_lvl[lvl]:
                filter_ids[lvl] = ids[lvl]
                filter_nb += 1

        if filter_nb > 0:
            logging.info("Filter ids: %s" % filter_ids)
            json_file = rdf_handler.create_JSON(x_type, y_type, message['lvl'], filter_ids)
        else:
            json_file = rdf_handler.create_JSON(x_type, y_type, message['lvl'])
        # Send json file to webserver
        socketio.emit('new_plot', {'data' : json_file, 'lvl': message['lvl']}, namespace='/socketio')
        # Get data ids
        # ids = rdf_handler.get_ids(x_type, y_type)
        all_ids = rdf_handler.get_ids(x_type, y_type, message['lvl'])
        list_ids = [int(id) for id in all_ids]
        logging.info("List of ids: %s" % list_ids)
        # Send data ids to PyMol
        if moliscope:
            liblo.send((osc_client, osc_port), "/moliscope/set_level", message['lvl'])
            liblo.send((osc_client, osc_port), "/moliscope/ids", list_ids)
        else:
            liblo.send((osc_client, osc_port), "/ids", list_ids)

@socketio.on('update_context', namespace='/socketio')
def change_scale(message):
    global context
    logging.info("Update current context level to: "+message['data'])
    context = message['data']

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
        help="The ip of the OSC client")
    parser.add_argument("--client_port", type=int, default=5555,
        help="The port the OSC client is listening on")
    parser.add_argument("--server_ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--server_port", type=int, default=8100,
        help="The port the OSC server is listening on")
    parser.add_argument("--ip", default="0.0.0.0",
        help="The ip of the web server")
    parser.add_argument("--port", type=int, default=5000,
        help="The port the web server is hosted")
    parser.add_argument("--moliscope", type=bool, default=False,
        help="Moliscope mode True/False")
    parser.add_argument("--debug", type=bool, default=True,
        help="Debug mode True/False")
    args = parser.parse_args()

    logging.info("\nWeb server \nIP: %s \t PORT: %d \t Debug: %s \nOSC server\nIP: %s \t PORT: %d\n" % (args.ip, args.port, args.debug, args.client_ip, args.client_port))

    # send all messages to port client_port on the local machine
    # try:
    #     #target = liblo.Address(args.client_port)
    #     target = liblo.Address('chm6048.limsi.fr', args.client_port)
    #     logging.info("Initialization of sender adress on %s" % target.url)
    #     logging.info(target.url)
    # except liblo.AddressError, err:
    #     print str(err)
    #     sys.exit()

    # Define global variable
    osc_client = args.client_ip
    osc_port = args.client_port
    moliscope = args.moliscope

    logging.info("Client url -> %s:%s \nMoliscope mode -> %s" % (osc_client, osc_port, moliscope))
    # osc_thread = threading.Thread(target=create_osc_server, args=(args.server_port,))
    # osc_thread.start()

    # osc_client = udp_client.UDPClient(args.osc_ip, args.osc_port)

    #app.run(host=args.ip, port=args.port, debug=args.debug)
    socketio.run(app, host=args.ip, port=args.port)


