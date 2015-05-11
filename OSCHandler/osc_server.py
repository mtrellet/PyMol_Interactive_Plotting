from liblo import ServerThread, make_method, Address
import logging
# logging.basicConfig(filename="osc_server_session.log", filemode="w", level=logging.INFO)


class MyServer(ServerThread):
    def __init__(self, port, pymol_handler = None):
        """
        Initialize an OSC server to listen to specific port
        :param port: OSC port
        :param pymol_handler: PyMol associated app
        """
        logging.info("Initialization of OSC server on port: %d " % port)
        ServerThread.__init__(self, port)
        logging.info("Server running on %s " % self.url)
        #self.target = Address(port)
        self.selected_models = []
        self.pymol_handler = pymol_handler


    @make_method('/selected', 'b')
    def selected_callback(self, path, args, types, src, data):
        print args
        if self.pymol_handler:
            selected = args[0]
            logging.info("received message '%s' with arguments: %s" % (path, args))
            self.selected_models = selected
            self.pymol_handler.new_selected_models(self.selected_models)

    @make_method('/new_plots', 'ss')
    def new_plots_callback(self, path, args):
        logging.info(args)

    @make_method(None, None)
    def fallback(self, path, args):
        logging.info("received unknown message '%s'" % path)