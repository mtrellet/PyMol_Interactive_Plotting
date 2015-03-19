'''
See more here: http://www.pymolwiki.org/index.php/dynoplot

###############################################
#  File:          interactive_plotting.py
#  Author:        Dan Kulp
#  Creation Date: 8/29/05
#
#  Modified 2011-11-17 by Thomas Holder
#  Modified 2015-01-15 by Mikael Trellet
#
#  Notes:
#  Draw plots that display interactive data
#  Added:   * back-and-forth communication.
#           * RDF parsing and querying with SPARQL
#   RMSD plot shown over trajectory.
###############################################
'''

from __future__ import division
from __future__ import generators

import Tkinter
from Tkinter import BooleanVar
from tkinter_plot import SimplePlot
from pymol import cmd, util
from pymol.wizard import Wizard
import math
import time
import Queue
import threading
import logging
from RDF_handling import RDF_Handler
import trace
import color_by_residue
from guppy import hpy
from memory_profiler import profile

# Parameters of logging output
import logging
logging.basicConfig(filename='pymol_session.log',filemode='w',level=logging.INFO)
#logging.getLogger().addHandler(logging.StreamHandler())

# workaround: Set to True if nothing gets drawn on canvas, for example on linux with "pymol -x"
with_mainloop = False
# Global variables for pymol event checking
myspace = {'previous':set(), 'models':set(), 'residues':set()}
previous_mouse_mode = cmd.get("mouse_selection_mode")
locked = False

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
        return [[ 1, 'Mode of selection',''], [ 2, 'Selection by atom','cmd.set("mouse_selection_mode", 0);cmd.refresh_wizard()'], [ 2, 'Selection by residues','cmd.set("mouse_selection_mode", 1);cmd.refresh_wizard()'], [ 2, 'Selection by chain','cmd.set("mouse_selection_mode", 2);cmd.refresh_wizard()'], [ 2, 'Selection by model','cmd.set("mouse_selection_mode", 5);cmd.refresh_wizard()'], [ 2, 'Clear Selection','cmd.delete("'+self.sele_name+'");cmd.refresh_wizard()'],]


"""Rect Tracker class for Python Tkinter Canvas"""
"""http://code.activestate.com/recipes/577409-python-tkinter-canvas-rectangle-selection-box/"""

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

class RectTracker:
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.item = None
        
    def draw(self, start, end, **opts):
        """Draw the rectangle"""
        return self.canvas.create_rectangle(*(list(start)+list(end)), **opts)
        
    def autodraw(self, **opts):
        """Setup automatic drawing; supports command option"""
        self.start = None
        self.canvas.bind("<Button-1>", self.__update, '+')
        self.canvas.bind("<B1-Motion>", self.__update, '+')
        self.canvas.bind("<ButtonRelease-1>", self.__stop, '+')
        self.canvas.bind("<Button-2>", self.__accumulate, '+')
        self.canvas.bind("<B2-Motion>", self.__accumulate, '+')
        self.canvas.bind("<ButtonRelease-2>", self.__release, '+')
        
        self._command = opts.pop('command', lambda *args: None)
        self.rectopts = opts


    def __accumulate(self, event):
        if not self.start:
            self.start = [event.x, event.y]
            return

        if self.item is not None:
            self.canvas.delete(self.item)
        self.item = self.draw(self.start, (event.x, event.y), **self.rectopts)
        #self._command(self.start, (event.x, event.y))

    def __release(self,event):
        self.canvas.delete(self.item)
        self._command(self, self.canvas, self.start, (event.x, event.y), "all_in_one")
        self.start = None
        self.item = None

    def __update(self, event):
        if not self.start:
            self.start = [event.x, event.y]
            return
        
        if self.item is not None:
            self.canvas.delete(self.item)
        self.item = self.draw(self.start, (event.x, event.y), **self.rectopts)
        self._command(self, self.canvas, self.start, (event.x, event.y), "update")
        
    def __stop(self, event):
        self.start = None
        self.canvas.delete(self.item)
        self.item = None
        
    def hit_test(self, start, end, tags=None, ignoretags=None, ignore=[]):
        """
        Check to see if there are items between the start and end
        """
        ignore = set(ignore)
        ignore.update([self.item])
        
        # first filter all of the items in the canvas
        if isinstance(tags, str):
            tags = [tags]
        
        if tags:
            tocheck = []
            for tag in tags:
                tocheck.extend(self.canvas.find_withtag(tag))
        else:
            tocheck = self.canvas.find_all()
        tocheck = [x for x in tocheck if x != self.item]
        if ignoretags:
            if not hasattr(ignoretags, '__iter__'):
                ignoretags = [ignoretags]
            tocheck = [x for x in tocheck if x not in self.canvas.find_withtag(it) for it in ignoretags]
        
        self.items = tocheck
        
        # then figure out the box
        xlow = min(start[0], end[0])
        xhigh = max(start[0], end[0])
        
        ylow = min(start[1], end[1])
        yhigh = max(start[1], end[1])
        
        items = []
        for item in tocheck:
            if item not in ignore:
                if item in self.canvas.shapes:
                    x, y = average(groups(self.canvas.coords(item)))
                    if (xlow < x < xhigh) and (ylow < y < yhigh):
                        items.append(item)
    
        return items


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
        rootframe = Tkinter.Tk()
        parent = rootframe

        rootframe.title(' Interactive Analyses')
        rootframe.protocol("WM_DELETE_WINDOW", self.close_callback)

        self.canvas = []

        ###############################
        ##### NEW WINDOW FOR RMSD #####
        ###############################

        self.create_window(parent, 500, 500, 0, 50, 0, 0.27, symbols, Tkinter.LEFT, "Time Frame", "RMSD")

        if name is None:
            try:
                name = cmd.get_unused_name('Handler')
            except AttributeError:
                name = 'Handler'

        self.rdf_handler = RDF_Handler("/Users/trellet/Dev/Protege_OWL/data/mod_res_pt_parsed.ntriples")
        self.queue = queue
        self.rootframe = rootframe
        self.current_canvas = self.canvas[-1]
        self.name = name
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
        self.scale = 'model'
        self.models_selected = 0
        self.item_selected = 0
        self.current_state = "default"

        self.create_main_buttons()

        if name != 'none':
            auto_zoom = cmd.get('auto_zoom')
            cmd.set('auto_zoom', 0)
            cmd.load_callback(self, name)
            cmd.set('auto_zoom', auto_zoom)
            # canvas.bind("<ButtonPress-1>", canvas.down)
            # canvas.bind("<ButtonRelease-1>", canvas.up)
            # canvas.bind("<Motion>", canvas.drag)

        ######
        # Call to selection tool
        rect = RectTracker(self.current_canvas)
        rect.autodraw(fill="", width=1, command=self.onDrag)

        delete = Tkinter.Button(self.rootframe, text = "Delete", command = lambda: self.delete(self.canvas[0]), anchor = "w")
        delete.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        delete_window = self.current_canvas.create_window(210, 445, anchor="sw", window=delete)

        #####
        # Call to wizard tool
        wiz = PickWizard(self)

        # make this the active wizard

        cmd.set_wizard(wiz)

        # wiz.register_observer(self.notify)
        # wiz.notify_observers('test')

        #self.rootframe.after(500, self.update_plot_multiple)
        self.update_plot_multiple()
        #####


        ######################################
        ##### NEW WINDOW FOR TEMPERATURE #####
        ######################################

        self.create_window(parent, 500, 500, 0, 50, 250, 320, symbols, Tkinter.LEFT, "Time Frame", "Temperature")

        #####
        # Call to selection tool
        rect2 = RectTracker(self.current_canvas)
        rect2.autodraw(fill="", width=1, command=self.onDrag)
        

        delete2 = Tkinter.Button(self.rootframe, text = "Delete", command = lambda: self.delete(self.canvas[1]), anchor = "w")
        delete2.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        delete_window2 = self.current_canvas.create_window(210, 445, anchor="sw", window=delete2)


        #################################
        ##### NEW WINDOW FOR ENERGY #####
        #################################

        # self.create_window(parent, 500, 500, 0, 50, 20000, 22800, symbols, Tkinter.LEFT, "Time Frame", "Energy")

        # #####
        # # Call to selection tool
        # rect3 = RectTracker(self.current_canvas)
        # rect3.autodraw(fill="", width=1, command=self.onDrag)
        # #####

        # delete3 = Tkinter.Button(self.rootframe, text = "Delete", command = lambda: self.delete(self.canvas[2]), anchor = "w")
        # delete3.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        # delete_window3 = self.current_canvas.create_window(210, 445, anchor="sw", window=delete3)


        if selection is not None:
            self.start(self.canvas[0], 'time_frame', 'RMSD')
            self.start(self.canvas[1], 'time_frame', 'temperature')
            #self.start(self.canvas[2], 'time_frame', 'energy')


        self.create_option_buttons()


        if with_mainloop and pmgapp is None:
            rootframe.mainloop()

        #############################################
        ##### CREATE CANVAS ITEM IDs DICTIONARY #####
        #############################################
        self.create_ids_equivalent_dict()


    ######
    # Command to select by dragging
    def onDrag(self, rect, canvas, start, end, mode):
        global x,y, locked
        if mode == "update":
            items = rect.hit_test(start, end)
            display=set()
            for x in rect.items:
                # if x not in items:
                #     if x in canvas.shapes:
                #         canvas.itemconfig(x, fill='grey')
                #         if self.show[canvas.shapes[x][5][1]-1]:
                #             cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                #             cmd.hide('line', '(sele)')
                # else:
                if x in items:
                    #canvas.itemconfig(x, fill='blue')
                    if x in canvas.shapes:
                        display.add(canvas.shapes[x][5][1])
                        # cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                        # cmd.show('line', '(sele)')
                        logging.debug(display)
                        self.show[canvas.shapes[x][5][1]-1] = True
                        locked = False
            self.update_plot_multiple(1, display, canvas)
            if len(display) == 0 and not locked:
                self.update_plot_multiple(1, display, canvas)
                locked = True
        elif mode == "all_in_one":
            logging.info("START/END: %d:%d / %d:%d" % (start[0], start[1], end[0], end[1]))
            x_low, x_high, y_low, y_high = canvas.convertToValues(start, end)
            logging.info("Value limits: x=[%f -> %f]\ny=[%f -> %f]" % (x_low, x_high, y_low, y_high))
            models_selected = self.rdf_handler.query_sub_rdf(canvas, x_low, x_high, y_low, y_high)
            logging.info(models_selected)
            for model in models_selected:
                self.show[model-1] = True
            self.update_plot_multiple(1, models_selected, canvas)
        #####

    def propose_analyses(self, scale):
        from Tkinter import BooleanVar
        self.scale = scale.lower()

        qres = self.rdf_handler.get_analyses(self.scale)

        if len(qres) > 0:
            new_window = Tkinter.Tk()
            new_window.title(' Display plots ')
            #f = Tkinter.Frame(new_window)
            #new_window.protocol("WM_DELETE_WINDOW", self.close_window)
            # c = Tkinter.Canvas(new_window, width=100, height=len(qres) * 40)
            # c.pack(fill="both", expand=1)
            text_id = Tkinter.Label(new_window, text="We have found the following plots:" )
            text_id.pack(side=Tkinter.TOP)
            self.checkbuttons = []
            self.choices = []
            self.button_dict = {}
            cpt = 0
            for i in qres:
                var = BooleanVar(new_window)
                checkbutton = Tkinter.Checkbutton(new_window, text=i[0]+" / "+i[1], variable = var, onvalue=True, offvalue=False, height = 5, width = 20)
                checkbutton.pack(side=Tkinter.TOP)
                self.choices.append(var)
                #self.checkbuttons.append(checkbutton)
                self.button_dict[cpt] = [i[0], i[1], self.choices[-1]]
                cpt+=1
            send_button = Tkinter.Button(new_window, text="Send", command= self.display_plots)
            send_button.pack(side=Tkinter.TOP)
        else:
            new_window = Tkinter.Tk()
            text_id = Tkinter.Label(new_window, text="We did not found any preprocessed plots\nThese are the possible analyses to be performed: ")
            text_id.pack(side=Tkinter.TOP)
            self.current_window = new_window
            self.choices = []
            self.button_dict = {}
            if self.scale == "residue" or self.scale == "atom":
                for ana in self.proposed_analyses:
                    var = BooleanVar(self.current_window)
                    checkbutton = Tkinter.Checkbutton(self.current_window, text=self.scale+"_id / "+ana, variable = var, onvalue=True, offvalue=False, height = 5, width = 20)
                    checkbutton.pack(side=Tkinter.TOP)
                    self.choices.append(var)
                    self.button_dict[ana] = self.choices[-1]
                send_button = Tkinter.Button(self.current_window, text="Send", command=self.calc_plots)
                send_button.pack(side=Tkinter.TOP)


        new_window.mainloop()

####### NEW ANALYSES ###########################################################################
#
#
#
    def calc_plots(self):
        # Delete former canvas
        self.current_window.destroy()
        new_window = Tkinter.Tk()
        self.current_window = new_window
        self.current_window.title("Model of reference?")
        if len(self.models_shown) > 0:
            models = [model for model in self.models_shown]
        else:
            iterat = {'tmp' : set()}
            cmd.iterate('(all)', 'tmp.add(model)', space=iterat)
            models = [int(model) for model in iterat['tmp']]
        if not models:
            text_id = Tkinter.Label(self.current_window, text="No model found..!")
            text_id.pack(side=Tkinter.TOP)
        else:
            # 1st solution -> The user selects a model in the viewer
            text_manual = Tkinter.Label(self.current_window, text="Select the model you want as a reference.\n\n OR\n\n")
            text_manual.pack(side=Tkinter.TOP)
            cmd.set("mouse_selection_mode", 5)
            if len(self.models_shown) == 0:
                self.update_plot_multiple(source=3)
            self.current_state = "selection"
            # 2nd solution -> The user chooses a model in a list
            text_id = Tkinter.Label(self.current_window, text="Choose the model you want in the list:")
            text_id.pack(side=Tkinter.TOP)
            scrollbar = Tkinter.Scrollbar(self.current_window, orient=Tkinter.VERTICAL)
            models_listbox = Tkinter.Listbox(self.current_window,yscrollcommand=scrollbar.set)
            scrollbar.config(command=models_listbox.yview)
            scrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
            models_listbox.pack(side=Tkinter.TOP)
            models.sort()
            for m in models:
                models_listbox.insert(Tkinter.END, m)
            models_listbox.bind('<<ListboxSelect>>', self.on_model_selected)
#
#
    def on_model_selected(self, evt):
        if evt is not None:
            w = evt.widget
            index = int(w.curselection()[0])
            self.model_selected = w.get(index)
            for k,s in self.current_canvas.ids_ext.iteritems():
                if s[5][1] == self.model_selected:
                    self.current_canvas.picked = k
            # tmp = set()
            # tmp.add(self.model_selected)
            # self.update_plot_multiple(source=0, to_display=tmp)
        logging.info('Model selected: %d' % (self.model_selected))
        dic = {}
        for k,s in self.button_dict.iteritems():
            logging.info("%s : %d" % (k, s.get()))
            x_type = ""
            y_type = ""
            if s:
                if k == "distance":
                    # Get list of items for the specified scale
                    item_list, indiv_list = self.rdf_handler.get_id_indiv_from_RDF(self.model_selected)
                    self.current_window.destroy()
                    current_window = Tkinter.Tk()
                    current_window.title(' Item of reference? ')
                    current_window.protocol("WM_DELETE_WINDOW", self.close_callback)
                    #self.rootframe = rootframe
                    self.current_window = current_window
                    # 1st solution -> The user selects a model in the viewer
                    text_manual = Tkinter.Label(self.current_window, text="Select the "+str(self.scale)+" you want as a reference.\n\n OR\n\n")
                    text_manual.pack(side=Tkinter.TOP)
                    cmd.set("mouse_selection_mode", 1)
                    self.current_state = "selection"
                    text_id = Tkinter.Label(self.current_window, text="Choose your "+self.scale+" of reference in the list:")
                    text_id.pack(side=Tkinter.TOP)
                    scrollbar = Tkinter.Scrollbar(self.current_window, orient=Tkinter.VERTICAL)
                    items_listbox = Tkinter.Listbox(self.current_window,yscrollcommand=scrollbar.set)
                    scrollbar.config(command=items_listbox.yview)
                    scrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
                    items_listbox.pack(side=Tkinter.TOP)
                    for i in item_list:
                        items_listbox.insert(Tkinter.END, i)
                    items_listbox.bind('<<ListboxSelect>>', self.on_reference_selected_for_distance)
                    if self.scale == "residue":
                        x_type = "resid"
                    else:
                        x_type = "atomid"
                    y_type = "distance"
            # Formatting new dictionary to be used in display_plots()
            dic[k] = [x_type, y_type, s]
        self.button_dict = dic

    def on_reference_selected_for_distance(self, evt):
        # Close previous window when selection done
        if evt is not None:
            w = evt.widget
            ref = int(w.curselection()[0])
            self.item_selected = w.get(ref)
        logging.info("Item selected: %d" % self.item_selected)
        
        self.rdf_handler.add_distance_points(self.item_selected, self.model_selected, self.scale)
        #self.rdf_graph.serialize("test.ntriples", format="nt")
        self.display_plots()
        self.update_plot_multiple()
#
#
###################################################################################################

    def display_plots(self):
        """ Display new plots according to user choice(s) """
        # Delete former canvas and former windows
        self.current_window.destroy()
        self.rootframe.destroy()
        rootframe = Tkinter.Tk()
        rootframe.title(' Interactive Analyses')
        rootframe.protocol("WM_DELETE_WINDOW", self.close_callback)
        self.rootframe = rootframe
        self.canvas = []
        self.current_canvas = None
        # 1st case: We come from known analyses and just redraw
        # 2nd case: We come from new analyses we just calculated
        logging.info("Status of checkbuttons:")
        for k,s in self.button_dict.iteritems():
            logging.info("%s / %s : %d for %s" % (s[0], s[1], s[2].get(), self.scale))
            if s[2].get():
                xmin, xmax, ymin, ymax = self.rdf_handler.get_mini_maxi_values(s[0], s[1], self.scale)
                logging.info("xmin / xmax / ymin / ymax: %f %f %f %f" % (xmin, xmax, ymin, ymax))
                self.create_window(self.rootframe, 500, 500, xmin, xmax, ymin*0.90, ymax*1.10, '', Tkinter.LEFT, s[0], s[1])

                rect = RectTracker(self.current_canvas)
                rect.autodraw(fill="", width=1, command=self.onDrag)
                self.rect_trackers.append(rect)

                delete = Tkinter.Button(self.rootframe, text = "Delete", command = lambda: self.delete(self.canvas[-1]), anchor = "w")
                delete.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
                delete_window = self.current_canvas.create_window(210, 445, anchor="sw", window=delete)
                self.delete_buttons.append(delete)

                if len(self.canvas) == 1:
                    self.create_main_buttons()

                self.start(self.canvas[-1], s[0], s[1])

        self.create_option_buttons()

        self.create_ids_equivalent_dict()

        rootframe.mainloop()

    def create_option_buttons(self):
        options = Tkinter.Canvas(self.rootframe, width=200, height=500)
        options.pack()

        options.create_line(2,10,2,490, fill='black', width=1)

        model = Tkinter.Button(self.rootframe, text='MODEL', command = lambda: self.propose_analyses('MODEL'))
        model.configure(width=8, activebackground = "#FF0000", relief='raised')
        model_window = options.create_window(100, 40, window=model)
        
        chain = Tkinter.Button(self.rootframe, text='CHAIN', command = lambda: self.propose_analyses('CHAIN'))
        chain.configure(width=8, activebackground = "#FF0000", relief='raised')
        chain_window = options.create_window(100, 70, window=chain)
        
        residue = Tkinter.Button(self.rootframe, text='RESIDUE', command = lambda: self.propose_analyses('RESIDUE'))
        residue.configure(width=8, activebackground = "#FF0000", relief='raised')
        residue_window = options.create_window(100, 100, window=residue)

        atom = Tkinter.Button(self.rootframe, text='ATOM', command = lambda: self.propose_analyses('ATOM'))
        atom.configure(width=8, activebackground = "#FF0000", relief='raised')
        atom_window = options.create_window(100, 130, window=atom)
                    

    def create_main_buttons(self):
        reset = Tkinter.Button(self.rootframe, text = 'RESET', command = lambda: self.update_plot_multiple(2), anchor = "w")
        reset.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        reset_window = self.current_canvas.create_window(40, 490, anchor="sw", window=reset)

        select = Tkinter.Button(self.rootframe, text = 'SELECT FROM VIEWER', command = lambda: self.update_plot_multiple(3), anchor = "w")
        select.configure(width = 19, activebackground = "#33B5E5", relief = "raised")
        select_window = self.current_canvas.create_window(270, 490, anchor="se", window=select)

        self.current_canvas.create_line(40, 455, 300, 455, fill='black', width=1)


    def create_ids_equivalent_dict(self):
        """ Create a dictionary of equivalent ids for each canvas created """
        for canv in self.canvas:
            canv.ids_ext = {}
        for k,s in self.canvas[0].shapes.iteritems():
            self.canvas[0].ids_ext[k] = []
            for canv in self.canvas[1:]:
                for k1,s1 in canv.shapes.iteritems():
                    if s1[5][1] == s[5][1]:
                        self.canvas[0].ids_ext[k].append(k1)

        for i in range(1,len(self.canvas)):
            self.canvas[i].ids_ext = {v[i-1]: [item for sublist in [[k], v[:i-1], v[i:]] for item in sublist] for k,v in self.canvas[0].ids_ext.items()}

        logging.info("Dictionaries of equivalent ids created...")
        # logging.debug(self.canvas[0].shapes[192])
        # logging.debug(self.canvas[1].shapes[self.canvas[0].ids_ext[192][0]])
        # logging.debug(self.canvas[0].shapes[self.canvas[1].ids_ext[self.canvas[0].ids_ext[192][0]][0]])


    def update_plot_multiple(self, source =0, to_display=set(), canvas = None):
        """ Check for updated selections data in all plots simultaneously"""
        start_time = time.time()
        if canvas == None:
            canvas = self.current_canvas
        if source == 1:
            if self.scale == "model":
                logging.info("Display models sent by OnDrag: ")
                logging.info(to_display)
                self.models_to_display = to_display.intersection(self.all_models)
                logging.info(self.models_to_display)
                for k,s in canvas.shapes.iteritems():
                    if s[5][1] in self.models_to_display and s[5][1] not in self.models_shown:
                        canvas.itemconfig(k, fill='blue')
                        cpt = 0
                        for it in canvas.ids_ext[k]:
                            if self.canvas[cpt] != canvas:
                                self.canvas[cpt].itemconfig(it, fill='blue')
                            else:
                                cpt+=1
                                self.canvas[cpt].itemconfig(it, fill='blue')
                            cpt+=1
                        logging.debug("Color: %04d" % s[5][1])
                        #cmd.select('sele', '%04d' % s[5][1])
                        #cmd.show('cartoon', 'name CA and %04d' % s[5][1])
                        cmd.show('line', '%04d' % s[5][1])
                        #cmd.disable('sele')
                    elif s[5][1] not in self.models_to_display and s[5][1] in self.models_shown:
                        canvas.itemconfig(k, fill='grey')
                        cpt=0
                        for it in canvas.ids_ext[k]:
                            if self.canvas[cpt] != canvas:
                                self.canvas[cpt].itemconfig(it, fill='grey')
                            else:
                                cpt+=1
                                self.canvas[cpt].itemconfig(it, fill='grey')
                            cpt+=1
                        logging.debug("Hide: %04d" % s[5][1])
                        #cmd.select('sele', '%04d' % s[5][1])
                        cmd.hide('everything', '%04d' % s[5][1])
                        #cmd.disable('sele')
                self.models_shown = self.models_to_display 
            elif self.scale == "residue":
                logging.info("Display residues sent by OnDrag: ")
                logging.info(to_display)
                self.residues_to_display = to_display.intersection(self.all_residues)
                logging.info(self.residues_to_display)
                for k,s in canvas.shapes.iteritems():
                    if s[5][1] in self.residues_to_display and s[5][1] not in self.residues_shown:
                        canvas.itemconfig(k, fill='blue')
                        cpt = 0
                        for it in canvas.ids_ext[k]:
                            if self.canvas[cpt] != canvas:
                                self.canvas[cpt].itemconfig(it, fill='blue')
                            else:
                                cpt+=1
                                self.canvas[cpt].itemconfig(it, fill='blue')
                            cpt+=1
                        logging.debug("Stick: %04d" % s[5][1])
                        #cmd.select('sele', '%04d' % s[5][1])
                        #cmd.show('cartoon', 'name CA and %04d' % s[5][1])
                        cmd.show('sticks', 'resid %d and model %04d' % (s[5][1], self.model_selected))
                        #cmd.disable('sele')
                    elif s[5][1] not in self.residues_to_display and s[5][1] in self.residues_shown:
                        canvas.itemconfig(k, fill='grey')
                        cpt=0
                        for it in canvas.ids_ext[k]:
                            if self.canvas[cpt] != canvas:
                                self.canvas[cpt].itemconfig(it, fill='grey')
                            else:
                                cpt+=1
                                self.canvas[cpt].itemconfig(it, fill='grey')
                            cpt+=1
                        logging.debug("Line: %04d" % s[5][1])
                        #cmd.select('sele', '%04d' % s[5][1])
                        cmd.hide('sticks', 'resid %d and model %04d' % (s[5][1], self.model_selected))
                        # cmd.show('line', 'resid %d and model %04d' % (s[5][1], self.model_selected))
                        #cmd.disable('sele')
                self.residues_shown = self.residues_to_display

        elif source == 0:
            # Check single picking items
            for canv in self.canvas:
                if canv.picked != 0 and canv.picked != canv.previous:
                    canv.itemconfig(canv.picked, fill='blue')
                    cpt = 0
                    for it in canv.ids_ext[canv.picked]:
                        if self.canvas[cpt] != canv:
                            self.canvas[cpt].itemconfig(it, fill='blue')
                        else:
                            cpt+=1
                            self.canvas[cpt].itemconfig(it, fill='blue')
                        cpt+=1
                    cmd.show('cartoon', 'name CA and %04d' % canv.shapes[canv.picked][5][1])
                    cmd.show('lines', '%04d' % canv.shapes[canv.picked][5][1])
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
                        cmd.hide('everything', '%04d' % canv.shapes[canv.previous][5][1])
                    canv.previous = canv.picked
                    break # We can pick only one item among all canvas
            # Check selection from PyMol viewer
            try:
                items = self.queue.get_nowait()
                logging.info("Items from user selection in the viewer: "+str(items))
                logging.info("Current state: %s / Scale: %s" % (self.current_state, self.scale))
                
                # Automatic checking of model selection by the user
                if self.current_state == "default" and self.scale == "model":
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


    def create_window(self, parent, width, height, min_x, max_x, min_y, max_y, symbols, position, xtitle, ytitle):
        """ Create new plot window """
        canvas = SimplePlot(parent, width=width, height=height)
        #canvas.bind("<Button-2>", canvas.pickWhich)
        canvas.bind("<ButtonPress-3>", canvas.pickWhich)
        canvas.pack(side=position, fill="both", expand=1)
        x_gap = float(max_x-min_x) / 5
        y_gap = float(max_y - min_y) / 5
        xlabels = self.try_convert_to_int([float("{0:.2f}".format(min_x + i*x_gap)) for i in range(6)])
        ylabels = self.try_convert_to_int([float("{0:.2f}".format(min_y + i*y_gap)) for i in range(6)])
        canvas.axis(xlabels=xlabels, ylabels=ylabels, xtitle=xtitle, ytitle=ytitle)

        canvas.update()

        if symbols == 'ss':
            canvas.symbols = 1

        self.current_canvas = canvas
        self.canvas.append(canvas)

    def close_window(self):
        logging.info("WINDOW CLOSED")

    def close_callback(self):
        cmd.delete(self.name)
        self.rootframe.destroy()

    def start(self, canvas, x_query_type, y_query_type):
        self.lock = 1

        canvas.x_query_type = x_query_type
        canvas.y_query_type = y_query_type

        # Query points to draw first plot
        qres = self.rdf_handler.query_rdf(x_query_type, y_query_type, self.scale)

        if self.scale == "model":
            for row in qres:
                if int(row[2] not in self.all_models):
                    self.all_models.add(int(row[2]))
                model_index = ('all', int(row[2]))
                canvas.plot(float(row[0]), float(row[1]), model_index)
        elif self.scale == "residue":
            for row in qres:
                if int(row[2] not in self.all_residues):
                    self.all_residues.add(int(row[2]))
                residue_index = ('all', int(row[2]))
                canvas.plot(float(row[0]), float(row[1]), residue_index)
        self.lock = 0

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


def rama(sel='(all)', name=None, symbols='aa', filename=None, state=-1):
    '''
DESCRIPTION

    Ramachandran Plot
    http://pymolwiki.org/index.php/DynoPlot

ARGUMENTS

    sel = string: atom selection {default: all}

    name = string: name of callback object which is responsible for setting
    angles when canvas points are dragged, or 'none' to not create a callback
    object {default: Handler}

    symbols = string: aa for amino acid or ss for secondary structure {default: aa}

    filename = string: filename for postscript dump of canvas {default: None}
    '''
    queue = Queue.Queue()
    # Start background thread to check selections
    t = threading.Thread(target=check_selections, args=(queue,))
    t.start()
    logging.info("Checking changes in selections... (infinite loop)")
    dyno = Handler(queue, sel, name, symbols, int(state))
    if filename is not None:
        dyno.canvas.postscript(file=filename)

# Extend these commands
cmd.extend('ramachandran', rama)
cmd.auto_arg[0]['ramachandran'] = cmd.auto_arg[0]['zoom']

# Add to plugin menu
def __init_plugin__(self):
    queue = Queue.Queue()
    # Start background thread to check selections
    t = threading.Thread(target=check_selections, args=(queue,))
    t.start()
    logging.info("Checking changes in selections... (infinite loop)")
    self.menuBar.addcascademenu('Plugin', 'PlotTools', 'Plot Tools', label='Analyses Plot Tools')
    self.menuBar.addmenuitem('PlotTools', 'command', 'Launch Rama Plot', label='RMSD Plot',
                             command=lambda: Handler(queue, '(enabled)'))

# vi:expandtab:smarttab
