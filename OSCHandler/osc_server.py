from liblo import ServerThread, make_method, Address, ServerError
import logging
# logging.basicConfig(filename="osc_server_session.log", filemode="w", level=logging.INFO)
import sys


class MyServer(ServerThread):
    def __init__(self, port, pymol_handler = None, flask_server = None):
        """
        Initialize an OSC server to listen to specific port
        :param port: OSC port
        :param pymol_handler: PyMol associated app
        :param flask_server: Flask web server
        """
        logging.info("***************")
        logging.info("Initialization of OSC server on port: %d " % port)
        try:
            ServerThread.__init__(self, port)
        except ServerError, err:
            logging.info(str(err))
            sys.exit()
        logging.info("Server running on %s " % self.url)
        print self.url
        logging.info("***************")
        #self.target = Address(port)
        self.selected_models = []
        self.pymol_handler = pymol_handler
        self.flask_server = flask_server

    @make_method('/selected', 'b')
    def selected_callback(self, path, args, types, src, data):
        if self.pymol_handler:
            selected = args[0]
            logging.info("received message '%s' with arguments: %s" % (path, args))
            self.selected_models = selected
            self.pymol_handler.new_selected_models(self.selected_models)

    @make_method('/selected', 'i')
    def no_selected_callback(self, path, args):
        logging.info("received message '%s' with arguments: %s" % (path, args))
        self.selected_models = []
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

    @make_method(None, None)
    def fallback(self, path, args):
        logging.info("received unknown message '%s' on '%s'" % (args, path))
        if path == '/selected':
            self.no_selected_callback(path, args)