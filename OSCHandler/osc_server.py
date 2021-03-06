from liblo import ServerThread, make_method, Address, ServerError, Server
import logging
# logging.basicConfig(filename="osc_server_session.log", filemode="w", level=logging.INFO)
import sys
import threading


class MyServer(Server):
    def __init__(self, port, pymol_handler=None, flask_server=None):
        """
        Initialize an OSC server to listen to specific port
        :param port: OSC port
        :param pymol_handler: PyMol associated app
        :param flask_server: Flask web server
        """
        logging.info("***************")
        logging.info("1) Free the desired port")
        try:
            server = Server(port)
            server.free()
        except ServerError, err:
            logging.info(str(err))
            sys.exit()
        logging.info("Port %s now free" % port)
        logging.info("2) Initialization of OSC server on port: %d " % port)
        try:
            Server.__init__(self, port)
        except ServerError, err:
            logging.info(str(err))
            sys.exit()
        logging.info("Server running on %s " % self.url)
        logging.info("***************")
        for t in threading.enumerate():
            print t
        #self.target = Address(port)
        self.selected_models = []
        self.pymol_handler = pymol_handler
        self.flask_server = flask_server

    @make_method('/selected', 'b')
    def selected_callback(self, path, args, types, src, data):
        if self.pymol_handler:
            selected = args[0]
            logging.info("/selected blob received message '%s' with arguments: %s" % (path, args))
            self.selected_models = selected
            self.pymol_handler.new_selected_models(self.selected_models)

    @make_method('/selected', 'i')
    def no_selected_callback(self, path, args):
        logging.info("/selected int received message '%s' with arguments: %s" % (path, args))
        self.selected_models = [args[0]]
        self.pymol_handler.new_selected_models(self.selected_models)

    @make_method('/new_plots', 'ss')
    def new_plots_callback(self, path, args):
        logging.info(args)

    @make_method('/ids', 'b')
    def new_ids_callback(self, path, args, types, src, data):
        if self.pymol_handler:
            ids = args[0]
            logging.info("received message '%s' with arguments: %s" % (path, args))
            self.pymol_handler.set_new_ids(ids)

    @make_method('/hide_level', 's')
    def hide_level_callback(self, path, args):
        if self.pymol_handler:
            logging.info("received message '%s' with arguments: %s" % (path, args))
            self.pymol_handler.hide_lvl(args[0])

    @make_method('/new_submodel_selection', None)
    def new_subselection_callback(self, path, args, types, src, data):
        if self.pymol_handler:
            logging.info("received message '%s' with arguments: %s" % (path, args))
            self.pymol_handler.new_subselection(args)

    @make_method(None, None)
    def fallback(self, path, args):
        logging.info("received unknown message '%s' on '%s'" % (args, path))
        if path == '/selected':
            self.no_selected_callback(path, args)