"""
See more here: http://www.pymolwiki.org/index.php/dynoplot

###############################################
#  File:          interactive_plotting.py
#  Author:        Dan Kulp
#  Creation Date: 8/29/05
#
#  Created 2011-11-17 by Thomas Holder
#  Modified 2015-01-15 by Mikael Trellet
#
#  Notes:
#  Draw plots that display interactive data
#  Added:   * back-and-forth communication.
#           * RDF parsing and querying with SPARQL
#   RMSD plot shown over trajectory.
###############################################
"""

from __future__ import division
from __future__ import generators

import time
import Queue
import threading
import json

from pymol import cmd, util
from pymol.wizard import Wizard
from OSCHandler.osc_server import MyServer
from interface.keyword2cmd import Keyword2Cmd

from RDFHandler.RDF_handling_distant import RDF_Handler
from utils import color_by_residue

import liblo
import sys

from multiprocessing.connection import Listener

# Parameters of logging output
import logging
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename="log/pymol_session.log", filemode="w", format=FORMAT, level=logging.INFO)
#logging.getLogger().addHandler(logging.StreamHandler())

# workaround: Set to True if nothing gets drawn on canvas, for example on linux with "pymol -x"
with_mainloop = False
# Global variables for pymol event checking
myspace = {'previous':set(), 'models':set(), 'residues':set()}
previous_mouse_mode = cmd.get("mouse_selection_mode")
locked = False

# Multi-threading queue init
queue = Queue.Queue()

class PickWizard(Wizard):

    def __init__(self, handler):
        self.sele_name = "sele" # must be set to "lb" for now...
        self.selected = []
        self.handler = handler
        # self.__observers = []

    # def register_observer(self, observer):
    #     self.__observers.append(observer)

    # def notify_observers(self, *args, **kwargs):
    #     for observer in self.__observers:
    #         observer(self, *args, **kwargs)

    def set_buttons(self):

        # just use selections (disable atom and bond picking)

        cmd.button('m','ctrl','+sele')
        cmd.button('r','ctrl','none')
        cmd.button('r','ctsh','none')

    def get_prompt(self):

        # returns prompt for the viewer window (optional)

        if self.sele_name in cmd.get_names('selections'):
            n_atom = cmd.count_atoms("sele")
        else:
            n_atom = 0
        if n_atom:
            list = cmd.identify("sele")
            return ["%d atoms selected..."%n_atom,str(list)]
        else:
            return ["Please select some atoms..."]

    def do_select(self,name):

        # handle mouse selection callback

        # if not "sele" in cmd.get_names('selections'):
        #     cmd.select("sele",'none')
        # cmd.enable("sele")
        cmd.refresh_wizard()

    def get_panel(self):
        return [[ 1, 'Mode of selection',''], [ 2, 'Selection by atom','cmd.set("mouse_selection_mode", 0);cmd.refresh_wizard()'],
                [ 2, 'Selection by residues','cmd.set("mouse_selection_mode", 1);cmd.refresh_wizard()'],
                [ 2, 'Selection by chain','cmd.set("mouse_selection_mode", 2);cmd.refresh_wizard()'],
                [ 2, 'Selection by model','cmd.set("mouse_selection_mode", 5);cmd.refresh_wizard()'],
                [ 2, 'Clear Selection','cmd.delete("'+self.sele_name+'");cmd.refresh_wizard()'],]


def groups(glist, numPerGroup=2):
    result = []

    i = 0
    cur = []
    for item in glist:
        if not i < numPerGroup:
            result.append(cur)
            cur = []
            i = 0

        cur.append(item)
        i += 1

    if cur:
        result.append(cur)

    return result

def average(points):
    aver = [0,0]
    
    for point in points:
        aver[0] += point[0]
        aver[1] += point[1]
        
    return aver[0]/len(points), aver[1]/len(points)

def check_selections(queue):
    """ Check if the selection made by the user changed """
    global previous_mouse_mode
    global myspace
    while True:
        # Check if the user changed the selection mode (atom/residue/chain/molecule)
        logging.debug("Current mouse selection mode : %d" % int(cmd.get("mouse_selection_mode")))
        logging.debug("Number of selections: %d" % len(cmd.get_names("selections")))
        if int(cmd.get("mouse_selection_mode")) == 5 and len(cmd.get_names("selections")) > 0:
            #logging.debug(cmd.get_names("selections")[1])
            nb_selected_objects = cmd.count_atoms('sele')
            if(nb_selected_objects > 0):
                logging.info("--- Selection made by the user ---")
                logging.info(nb_selected_objects)
                cmd.iterate('(sele)', 'models.add(model)', space=myspace)
                logging.info(myspace['models'])
                tmp = set()
                # Make the list with unique items
                for i in myspace['models']:
                    if int(i) not in tmp:
                        tmp.add(int(i))
                # Check if the selection has changed
                if tmp != myspace['previous']:
                    myspace['previous'] = tmp
                    queue.put(tmp)
                else:
                    time.sleep(1)
                cmd.select('none')
        elif int(cmd.get("mouse_selection_mode")) == 1 and len(cmd.get_names("selections")) > 0:
            #logging.debug(cmd.get_names("selections")[0])

            nb_selected_objects = cmd.count_atoms('sele')
            if(nb_selected_objects > 0):
                logging.info("--- Selection made by the user ---")
                cmd.iterate('(sele)', 'residues.add(resv)', space=myspace)
                logging.info(myspace['residues'])
                tmp = set()
                # Make the list with unique items
                for i in myspace['residues']:
                    if int(i) not in tmp:
                        tmp.add(int(i))
                # Check if the selection has changed
                if tmp != myspace['previous']:
                    myspace['previous'] = tmp
                    queue.put(tmp)
                    #cmd.delete('lb')
                else:
                    time.sleep(1)
                cmd.select('none')

        else:
            # if len(cmd.get_names("selections", enabled_only=1)) == 0:
            #     queue.put(set())
            #previous_mouse_mode = cmd.get("mouse_selection_mode")
            time.sleep(0.5)

class Handler:

    def __init__(self, queue, selection=None, name=None, symbols='', state=-1):
        # from pymol import _ext_gui as pmgapp
        # if pmgapp is not None:
        #     import Pmw
        #     rootframe = Pmw.MegaToplevel(pmgapp.root)
        #     parent = rootframe.interior()
        # else:

        if name is None:
            try:
                name = cmd.get_unused_name('Handler')
            except AttributeError:
                name = 'Handler'

        self.queue = queue

        self.lock = 0
        self.state = state
        self.show = [False]*251
        self.models_to_display = set()
        self.residues_to_display = set()
        self.all_models = set()
        self.all_residues = set()
        self.models_shown = set()
        self.residues_shown = set()
        self.choices = [] # Array of IntVar to store CHeckbuttons for user choices
        self.checkbuttons = []
        self.button_dict = {}
        self.rect_trackers = []
        self.delete_buttons = []
        self.proposed_analyses = ["distance", "x_position", "y_position", "z_position"]
        self.scale = 'Model'
        self.model_selected = 0
        self.item_selected = 0
        self.current_state = "default"
        self.color_selection = {0: "blue", 1:"red", 2:"yellow", 3:"black", 4:"orange"}
        self.x_choice = ""
        self.y_choice = ""
        self.params_plot = []
        self.options_button = None
        self.main_button = None
        self.osc_ip = "127.0.0.1"
        self.server_port = 8000
        self.client_port = 8100
        self.multi_port = 6000
        self.osc_receiver = []
        self.osc_sender = None

        # send all messages to port 1234 on the local machine
        # try:
        #     self.osc_sender = liblo.Address(self.server_port)
        #     logging.info("Initialization of sender adress on %s" % self.osc_sender.url)
        # except liblo.AddressError, err:
        #     print str(err)
        #     sys.exit()

        # for t in threading.enumerate():
        #     print t

        osc_thread = threading.Thread(target=self.create_osc_server, args=(self.server_port,))
        osc_thread.start()
        #
        # osc_thread2 = threading.Thread(target=self.create_osc_server, args=(self.client_port,))
        # osc_thread2.start()

        # osc_thread = threading.Thread(target=self.create_multiproc_server)
        # osc_thread.start()

        # for t in threading.enumerate():
        #     print t

        ######################################
        ##### NEW WINDOW FOR TEMPERATURE #####
        ######################################

        # if selection is not None:
        #     self.start('time_frame', 'rmsd_to_reference')
        #     self.start('time_frame', 'temperature')
            #self.start(self.canvas[2], 'time_frame', 'energy')


        # Send keyword command
        keywords = ['select', 'chain', 'A', 'model', 254]
        keyword2command = Keyword2Cmd(keywords)
        keyword2command.translate()

        #############################################
        ##### CREATE CANVAS ITEM IDs DICTIONARY #####
        #############################################
        # self.create_ids_equivalent_dict()

    def create_multiproc_server(self, port=6000):

        logging.info("Create OSC receiver and sender")
        # create server, listening on port 1234
        address = ('localhost', port)
        listener = Listener(address)
        conn = listener.accept()

        while True:
            msg = conn.recv()
            print msg
            if msg == 'close':
                conn.close()
                break
        #listener.close()


    def create_osc_server(self, port):
        logging.info("Create OSC receiver and sender")
        # create server, listening on port 1234
        try:
            print port
            self.osc_receiver.append(MyServer(port, pymol_handler=self))
            # self.osc_receiver = liblo.Server(self.server_port)
        except liblo.ServerError, err:
            print str(err)
            sys.exit()

        self.osc_receiver[-1].start()

        # register method taking a blob, and passing user data to the callback
        #self.osc_receiver.add_method("/selected", 'b', self.selected_callback, "user")

        # loop and dispatch messages every 100ms
        # while True:
        #     self.osc_receiver.recv(100)

    #
    # def selected_callback(self, path, args, types, src, data):
    #     print "received message '%s'" % path
    #     print "blob contains %d bytes, user data was '%s'" % (len(args[0]), data)
    #     print "data: %s" % (str(args[0]))
    #     to_display = set()
    #     if args[0]:
    #         for s in args[0]:
    #             to_display.add(s)
    #     self.update_plot_multiple(1,to_display)

    def new_selected_models(self, selected_models):
        to_display = set()
        for m in selected_models:
            to_display.add(m)
        self.update_plot_multiple(1, to_display)


    def update_plot_multiple(self, source =0, to_display=set(), canvas = None):
        """ Check for updated selections data in all plots simultaneously"""
        start_time = time.time()
        if source == 1:
            # Check mulltiple selection by dragging rectangle
            if self.scale == "Model":
                logging.info("Display models sent by OnDrag: ")
                logging.info(to_display)
                self.models_to_display = to_display.intersection(self.all_models)
                logging.info(self.models_to_display)
                #if self.correlate.get():
                for m in self.all_models:
                    if m in self.models_to_display:
                        logging.debug("Color: %04d" % m)
                        #cmd.select('sele', '%04d' % s[5][1])
                        #cmd.show('cartoon', 'name CA and %04d' % s[5][1])
                        cmd.show('line', '%04d' % m)
                        #cmd.disable('sele')
                    elif m in self.models_shown:
                        cmd.hide('line', '%04d' % m)

                self.models_shown = self.models_to_display
            #     elif s[5][1] not in self.models_to_display and s[5][1] in self.models_shown:
            #                 canvas.itemconfig(k, fill='grey')
            #                 cpt=0
            #                 for it in canvas.ids_ext[k]:
            #                     if self.canvas[cpt] != canvas:
            #                         self.canvas[cpt].itemconfig(it, fill='grey')
            #                     else:
            #                         cpt+=1
            #                         self.canvas[cpt].itemconfig(it, fill='grey')
            #                     cpt+=1
            #                 logging.debug("Hide: %04d" % s[5][1])
            #                 #cmd.select('sele', '%04d' % s[5][1])
            #                 cmd.hide('everything', '%04d' % s[5][1])
            #                 #cmd.disable('sele')
            #         self.models_shown = self.models_to_display
            #     else:
            #         for k,s in canvas.shapes.iteritems():
            #             if s[5][1] in canvas.selected:
            #                 canvas.itemconfig(k, fill=self.color_selection[self.canvas.index(canvas)])
            #             elif s[5][1] not in self.models_to_display:
            #                 canvas.itemconfig(k, fill='grey')
            #         show = canvas.selected
            #         tmp = []
            #         for canv in self.canvas:
            #             if len(canv.selected) > 0 and canv != canvas:
            #                 tmp = [val for val in show if val in canv.selected]
            #                 show = tmp
            #         for model in self.models_shown:
            #             if model in show:
            #                 cmd.show('line', '%04d' % model)
            #             else:
            #                 cmd.hide('everything', '%04d' % model)
            #         self.models_shown = show
            #
            # elif self.scale == "Residue":
            #     logging.info("Display residues sent by OnDrag: ")
            #     logging.info(to_display)
            #     self.residues_to_display = to_display.intersection(self.all_residues)
            #     logging.info(self.residues_to_display)
            #     for k,s in canvas.shapes.iteritems():
            #         if s[5][1] in self.residues_to_display and s[5][1] not in self.residues_shown:
            #             canvas.itemconfig(k, fill='blue')
            #             cpt = 0
            #             for it in canvas.ids_ext[k]:
            #                 if self.canvas[cpt] != canvas:
            #                     self.canvas[cpt].itemconfig(it, fill='blue')
            #                 else:
            #                     cpt+=1
            #                     self.canvas[cpt].itemconfig(it, fill='blue')
            #                 cpt+=1
            #             logging.debug("Stick: %04d" % s[5][1])
            #             #cmd.select('sele', '%04d' % s[5][1])
            #             #cmd.show('cartoon', 'name CA and %04d' % s[5][1])
            #             cmd.show('sticks', 'resid %d and model %04d' % (s[5][1], self.model_selected))
            #             #cmd.disable('sele')
            #         elif s[5][1] not in self.residues_to_display and s[5][1] in self.residues_shown:
            #             canvas.itemconfig(k, fill='grey')
            #             cpt=0
            #             for it in canvas.ids_ext[k]:
            #                 if self.canvas[cpt] != canvas:
            #                     self.canvas[cpt].itemconfig(it, fill='grey')
            #                 else:
            #                     cpt+=1
            #                     self.canvas[cpt].itemconfig(it, fill='grey')
            #                 cpt+=1
            #             logging.debug("Line: %04d" % s[5][1])
            #             #cmd.select('sele', '%04d' % s[5][1])
            #             cmd.hide('sticks', 'resid %d and model %04d' % (s[5][1], self.model_selected))
            #             # cmd.show('line', 'resid %d and model %04d' % (s[5][1], self.model_selected))
            #             #cmd.disable('sele')
            #     self.residues_shown = self.residues_to_display

        elif source == 0:
            # Check single picking items
            for canv in self.canvas:
                if canv.picked != 0 and canv.picked != canv.previous:
                    logging.info("Something has been picked")
                    canv.itemconfig(canv.picked, fill='blue')
                    cpt = 0
                    for it in canv.ids_ext[canv.picked]:
                        if self.canvas[cpt] != canv:
                            self.canvas[cpt].itemconfig(it, fill='blue')
                        else:
                            cpt+=1
                            self.canvas[cpt].itemconfig(it, fill='blue')
                        cpt+=1
                    if self.scale == "Model":
                        cmd.show('cartoon', 'name CA and %04d' % canv.shapes[canv.picked][5][1])
                        cmd.show('lines', '%04d' % canv.shapes[canv.picked][5][1])
                        logging.info("You selected item %d corresponding to model %d" % (canv.picked, canv.shapes[canv.picked][5][1]))
                    elif self.scale == "Residue":
                        cmd.show('sticks', 'resid %d and model %04d' % (canv.shapes[canv.picked][5][1], self.model_selected))
                        logging.info("You selected item %d corresponding to model %d" % (canv.picked, canv.shapes[canv.picked][5][1]))
                    if canv.previous != 0:
                        canv.itemconfig(canv.previous, fill='grey')
                        cpt=0
                        for it in canv.ids_ext[canv.previous]:
                            if self.canvas[cpt] != canv:
                                self.canvas[cpt].itemconfig(it, fill='grey')
                            else:
                                cpt+=1
                                self.canvas[cpt].itemconfig(it, fill='grey')
                            cpt+=1
                        if self.scale == "Model":
                            cmd.hide('everything', '%04d' % canv.shapes[canv.previous][5][1])
                        elif self.scale == "Residue":
                            cmd.hide('sticks', 'resid %d and model %04d' % (canv.shapes[canv.previous][5][1], self.model_selected))
                    canv.previous = canv.picked
                    break # We can pick only one item among all canvas
            # Check selection from PyMol viewer
            try:
                items = self.queue.get_nowait()
                logging.info("Items from user selection in the viewer: "+str(items))
                logging.info("Current state: %s / Scale: %s" % (self.current_state, self.scale))
                
                # Automatic checking of model selection by the user
                if self.current_state == "default" and self.scale == "Model":
                    self.models_to_display = items.intersection(self.all_models)
                    if len(self.models_to_display) > 0:
                        for k,s in canvas.shapes.iteritems():
                            if s[5][1] in self.models_to_display:
                                logging.info("Color red -> %04d" % s[5][1]) 
                                canvas.itemconfig(k, fill='blue')
                                cpt=0
                                for it in canvas.ids_ext[k]:
                                    if self.canvas[cpt] != canvas:
                                        self.canvas[cpt].itemconfig(it, fill='blue')
                                    else:
                                        cpt+=1
                                        self.canvas[cpt].itemconfig(it, fill='blue')
                                    cpt+=1
                                cmd.color('red', '%04d' % s[5][1])
                            else:
                                logging.info("Color default -> %04d" % s[5][1]) 
                                canvas.itemconfig(k, fill='grey')
                                cpt=0
                                for it in canvas.ids_ext[k]:
                                    if self.canvas[cpt] != canvas:
                                        self.canvas[cpt].itemconfig(it, fill='grey')
                                    else:
                                        cpt+=1
                                        self.canvas[cpt].itemconfig(it, fill='grey')
                                    cpt+=1
                                util.cbag('%04d' % s[5][1])
                                # cmd.select('sele', '%04d' % s[5][1])
                                # cmd.hide('line', '(sele)')
                        cmd.disable('lb')
                # We wait for user selection to trigger next steps
                elif self.current_state == "selection":
                    # Model selection
                    if int(cmd.get("mouse_selection_mode")) == 5:
                        try:
                            logging.info("Model selected for analyses: %d " % list(items)[0])
                            self.model_selected = list(items)[0]
                            cmd.hide('everything', 'all')
                            cmd.show('cartoon', '%04d' % self.model_selected)
                            cmd.show('lines', '%04d' % self.model_selected)
                            color_by_residue.color_by_restype()
                            for k,s in canvas.shapes.iteritems():
                                if s[5][1] == self.model_selected:
                                    canvas.itemconfig(k, fill='blue')
                                    cpt=0
                                    for it in canvas.ids_ext[k]:
                                        if self.canvas[cpt] != canvas:
                                            self.canvas[cpt].itemconfig(it, fill='blue')
                                        else:
                                            cpt+=1
                                            self.canvas[cpt].itemconfig(it, fill='blue')
                                        cpt+=1
                                else:
                                    logging.info("Color default -> %04d" % s[5][1]) 
                                    canvas.itemconfig(k, fill='grey')
                                    cpt=0
                                    for it in canvas.ids_ext[k]:
                                        if self.canvas[cpt] != canvas:
                                            self.canvas[cpt].itemconfig(it, fill='grey')
                                        else:
                                            cpt+=1
                                            self.canvas[cpt].itemconfig(it, fill='grey')
                                        cpt+=1
                                    # cmd.select('sele', '%04d' % s[5][1])
                            
                            #cmd.disable('lb')
                            self.current_state = "default"
                            self.on_model_selected(evt=None)
                            items = set()
                        except IndexError:
                            logging.info("No model selected in the viewer")
                            pass
                    # Residue selection
                    elif int(cmd.get("mouse_selection_mode")) == 1:
                        try:
                            logging.info("Residue selection for analyses: %d " % list(items)[0])
                            self.item_selected = list(items)[0]
                            items = set()
                            self.current_state = "default"
                            self.on_reference_selected_for_distance(evt=None)
                        except IndexError:
                            logging.info("No residue selected in the viewer")
                            pass

            except Queue.Empty:
                pass
        # Reset plot and viewer
        elif source == 2:
            logging.info("RESET")
            for canv in self.canvas:
                for k,s in canv.shapes.iteritems():
                    canv.itemconfig(k, fill='grey')
                    cpt=0
                    for it in canvas.ids_ext[k]:
                        if self.canvas[cpt] != canvas:
                            self.canvas[cpt].itemconfig(it, fill='grey')
                        else:
                            cpt+=1
                            self.canvas[cpt].itemconfig(it, fill='grey')
                        cpt+=1
                    self.models_to_display.clear()
                    self.models_shown.clear()
                canv.previous = 0
                canv.picked = 0
            cmd.hide('everything', 'all')
                
        # "Selection mode"
        elif source == 3:
            logging.info("SELECTION MODE")
            for canv in self.canvas:
                for k,s in canv.shapes.iteritems():
                    canv.itemconfig(k, fill='grey')
                    cpt=0
                    for it in canv.ids_ext[k]:
                        if self.canvas[cpt] != canv:
                            self.canvas[cpt].itemconfig(it, fill='grey')
                        else:
                            cpt+=1
                            self.canvas[cpt].itemconfig(it, fill='grey')
                        cpt+=1
                    self.models_to_display.add(s[5][1])
                    self.models_shown.add(s[5][1])
            cmd.show('cartoon', 'name CA')
            cmd.show('lines', 'all')

        logging.debug("---- %s seconds ----" % str(time.time()-start_time))
        try:
            self.rootframe.after(500, self.update_plot_multiple)
        except:
            pass

    def try_convert_to_int(self, array):
        result = []
        for a in array:
            f = float(a)
            i = int(f)
            if f != i:
                return array
            result.append(i)
        return result

    def close_callback(self):
        cmd.delete(self.name)
        self.rootframe.destroy()

    def __call__(self):
        if self.lock:
            return

        # Loop through each item on plot to see if updated
        # for value in self.canvas.shapes.itervalues():
        #     # Look for update flag...
        #     if value[2]:
        #         # Set residue's phi,psi to new values
        #         model, index = value[5]
        #         print " Re-setting Phi,Psi: %8.2f,%8.2f" % (value[3], value[4])
        #         set_phipsi(model, index, value[3], value[4], self.state)
        #         value[2] = 0


# def rama(sel='(all)', name=None, symbols='aa', filename=None, state=-1):
#     '''
# DESCRIPTION
#
#     Ramachandran Plot
#     http://pymolwiki.org/index.php/DynoPlot
#
# ARGUMENTS
#
#     sel = string: atom selection {default: all}
#
#     name = string: name of callback object which is responsible for setting
#     angles when canvas points are dragged, or 'none' to not create a callback
#     object {default: Handler}
#
#     symbols = string: aa for amino acid or ss for secondary structure {default: aa}
#
#     filename = string: filename for postscript dump of canvas {default: None}
#     '''
#     queue = Queue.Queue()
#     # Start background thread to check selections
#     t = threading.Thread(target=check_selections, args=(queue,))
#     t.start()
#     logging.info("Checking changes in selections... (infinite loop)")
#     dyno = Handler(queue, sel, name, symbols, int(state))
#     if filename is not None:
#         dyno.canvas.postscript(file=filename)

# Extend these commands
# cmd.extend('ramachandran', rama)
# cmd.auto_arg[0]['ramachandran'] = cmd.auto_arg[0]['zoom']

# Add to plugin menu
def __init_plugin__(self):
    #queue = Queue.Queue()
    # Start background thread to check selections
    t = threading.Thread(target=check_selections, args=(queue,))
    t.start()
    logging.info("Checking changes in selections... (infinite loop)")
    self.menuBar.addmenuitem('Plugin', 'command', 'Plot Tools', label='Distant Analyses Plot Tools', command=lambda: Handler(queue, '(enabled)'))
    #self.menuBar.addmenuitem('PlotTools', 'command', 'Launch Rama Plot', label='RMSD Plot',
    #                         command=lambda: Handler(queue, '(enabled)'))

# vi:expandtab:smarttab
