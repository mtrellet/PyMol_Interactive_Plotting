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
from pymol import cmd, util
from pymol.wizard import Wizard
import math
import time
import Queue
import threading
import logging

# Parameters of logging output
import logging
logging.basicConfig(filename='pymol_session.log',filemode='w',level=logging.INFO)
#logging.getLogger().addHandler(logging.StreamHandler())

# workaround: Set to True if nothing gets drawn on canvas, for example on linux with "pymol -x"
with_mainloop = False
# Global variables for pymol event checking
myspace = {'previous':set(), 'models':set()}
previous_mouse_mode = cmd.get("mouse_selection_mode")
locked = False


class PickWizard(Wizard):

    def __init__(self, handler):
        self.sele_name = "lb" # must be set to "lb" for now...
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

        cmd.button('m','ctrl','+lb')
        cmd.button('r','ctrl','none')
        cmd.button('r','ctsh','none')

    def get_prompt(self):

        # returns prompt for the viewer window (optional)

        if self.sele_name in cmd.get_names('selections'):
            n_atom = cmd.count_atoms(self.sele_name)
        else:
            n_atom = 0
        if n_atom:
            list = cmd.identify(self.sele_name)
            return ["%d atoms selected..."%n_atom,str(list)]
        else:
            return ["Please select some atoms..."]

    def do_select(self,name):

        # handle mouse selection callback

        if not self.sele_name in cmd.get_names('selections'):
            cmd.select(self.sele_name,'none')
        cmd.enable(self.sele_name)
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

    # def select_and_send(self, **opts):
    #     self.start = None
    #     self.canvas.bind("<Button-2>", self.__accumulate, '+')
    #     self.canvas.bind("<B2-Motion>", self.__accumulate, '+')
    #     self.canvas.bind("<ButtonRelease-2>", self.__release, '+')

    #     self._command = opts.pop('command', lambda *args: None)
    #     self.rectopts = opts

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
        self._command(self.start, (event.x, event.y), "all_in_one")
        self.start = None
        self.item = None

    def __update(self, event):
        if not self.start:
            self.start = [event.x, event.y]
            return
        
        if self.item is not None:
            self.canvas.delete(self.item)
        self.item = self.draw(self.start, (event.x, event.y), **self.rectopts)
        self._command(self.start, (event.x, event.y), "update")
        
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


class SimplePlot(Tkinter.Canvas):

    # Class variables
    mark_size = 4

    def __init__(self, *args, **kwargs):
        Tkinter.Canvas.__init__(self, *args, **kwargs)
        self.xlabels = []   # axis labels
        self.ylabels = []
        self.spacingx = 0   # spacing in x direction
        self.spacingy = 0
        self.xmin = 0       # min value from each axis
        self.ymin = 0
        self.xmax = 0
        self.ymax = 0
        self.lastx = 0      # previous x,y pos of mouse
        self.lasty = 0
        self.isdown = 0    # flag for mouse pressed
        self.item = (0,)    # items array used for clickable events
        self.shapes = {}    # store plot data, x,y etc..
        self.idx2resn = {}  # residue name mapping
        self.symbols = 0    # 0: amino acids, 1: secondary structure
        self.previous = 0   # Previous item selected
        self.picked = 0     # Item selected
        self.ids_ext = {}   # Dictionary of other canvas equivalent ids
        self.x_query_type = None
        self.y_query_type = None

    def axis(self, xmin=80, xmax=450, ymin=10, ymax=390, xint=390, yint=80, xlabels=[], ylabels=[], xtitle='X coordinates', ytitle='Y coordinates'):

        # Store variables in self object
        self.xlabels = xlabels
        self.ylabels = ylabels
        self.spacingx = (xmax - xmin) / (len(xlabels) - 1)
        self.spacingy = (ymax - ymin) / (len(ylabels) - 1)
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

        # Create axis lines
        self.create_line((xmin, xint, xmax, xint), fill="black", width=3)
        self.create_line((yint, ymin, yint, ymax), fill="black", width=3)

        # Create tick marks and labels
        self.create_text(3*xmax/4, ymax + 20,  text=(xtitle), anchor="nw")
        nextspot = xmin
        for label in xlabels:
            self.create_line((nextspot, xint + 5, nextspot, xint - 5), fill="black", width=2)
            self.create_text(nextspot, xint + 12, text=label)
            if len(xlabels) == 1:
                nextspot = xmax
            else:
                nextspot += (xmax - xmin) / (len(xlabels) - 1)

        self.create_text(20, ymin + 30, text="\n".join(ytitle), anchor="nw")
        nextspot = ymax
        for label in ylabels:
            self.create_line((yint + 5, nextspot, yint - 5, nextspot), fill="black", width=2)
            self.create_text(yint - 25, nextspot, text=label)
            if len(ylabels) == 1:
                nextspot = ymin
            else:
                nextspot -= (ymax - ymin) / (len(ylabels) - 1)


    # Plot a point
    def plot(self, xp, yp, meta):

        # Convert from 'label' space to 'pixel' space
        x = self.convertToPixel("X", xp)
        y = self.convertToPixel("Y", yp)

        #resn, color, ss = self.idx2resn.get(meta)

        # if self.symbols == 0:
        #     # symbols by amino acid (G/P/other)
        #     mark = {'GLY': 'Tri', 'PRO': 'Rect'}.get(resn, 'Oval')
        # else:
        #     # symbols by secondary structure
        #     mark = {'H': 'Oval', 'S': 'Rect'}.get(ss, 'Tri')

        # if mark == 'Oval':
        create_shape = self.create_oval
        coords = [x - self.mark_size, y - self.mark_size,
                  x + self.mark_size, y + self.mark_size]
        # elif mark == 'Tri':
        #     create_shape = self.create_polygon
        #     coords = [x, y - self.mark_size,
        #               x + self.mark_size, y + self.mark_size,
        #               x - self.mark_size, y + self.mark_size]
        # else:
        #     create_shape = self.create_rectangle
        #     coords = [x - self.mark_size, y - self.mark_size,
        #               x + self.mark_size, y + self.mark_size]

        # if color >= 0x40000000:
        #color = '#%06x' % (26 & 0xffffff)
        # else:
        #     color = '#%02x%02x%02x' % tuple([255 * i
        #                                      for i in cmd.get_color_tuple(color)])
        oval = create_shape(width=1, outline="black", fill="grey", *coords)
        self.shapes[oval] = [x, y, 0, xp, yp, meta]

    # Convet from pixel space to values
    def convertToValues(self, start, end):
        unit_per_pixel_x = float(abs(self.xlabels[-1]-self.xlabels[0])/abs(self.xmax-self.xmin))
        unit_per_pixel_y = float(abs(self.ylabels[-1]-self.ylabels[0])/abs(self.ymax-self.ymin))

        logging.info("Px/unit X: %f / Y: %f" % (unit_per_pixel_x, unit_per_pixel_y))

        x_low = (start[0]-self.xmin) * unit_per_pixel_x
        x_high = (end[0]-self.xmin) * unit_per_pixel_x
        y_low = (self.ymax-start[1]) * unit_per_pixel_y
        y_high = (self.ymax-end[1]) * unit_per_pixel_y

        if x_low > x_high:
            tmp = x_low
            x_low = x_high
            x_high = tmp

        if y_low > y_high:
            tmp = y_low
            y_low = y_high
            y_high = tmp

        return x_low, x_high, y_low, y_high

    def convertToPixel(self, axis, value):
        pixel_per_unit_x = float(abs(self.xmax-self.xmin)/abs(self.xlabels[-1]-self.xlabels[0]))
        pixel_per_unit_y = float(abs(self.ymax-self.ymin)/abs(self.ylabels[-1]-self.ylabels[0]))

        if axis == "Y":
            pixel = self.ymax - ((value-self.ylabels[0]) * pixel_per_unit_y)
        else:
            pixel = self.xmin + ((value-self.xlabels[0]) * pixel_per_unit_x)

        return pixel
        
    # Convert from pixel space to label space
    def convertToLabel(self, axis, value):

        # Defaultly use X-axis info
        label0 = self.xlabels[0]
        label1 = self.xlabels[1]
        spacing = self.spacingx
        min = self.xmin

        # Set info for Y-axis use
        if axis == "Y":
            label0 = self.ylabels[0]
            label1 = self.ylabels[1]
            spacing = self.spacingy
            min = self.ymin

        pixel = value - min
        label = pixel / spacing
        label = label0 + label * abs(label1 - label0)

        if axis == "Y":
            label = - label

        return label

    # Converts value from 'label' space to 'pixel' space
    # def convertToPixel(self, axis, value):

    #     # Defaultly use X-axis info
    #     label0 = self.xlabels[0]
    #     label1 = self.xlabels[1]
    #     spacing = self.spacingx
    #     min = self.xmin

    #     # Set info for Y-axis use
    #     if axis == "Y":
    #         label0 = self.ylabels[0]
    #         label1 = self.ylabels[1]
    #         spacing = self.spacingy
    #         min = self.ymin

    #     # Get axis increment in 'label' space
    #     inc = abs(label1 - label0)

    #     # 'Label' difference from value and smallest label (label0)
    #     diff = float(value - label0)

    #     # Get whole number in 'label' space
    #     whole = int(diff / inc)

    #     # Get fraction number in 'label' space
    #     part = float(float(diff / inc) - whole)

    #     # Return 'pixel' position value
    #     pixel = whole * spacing + part * spacing

    #     # Reverse number by subtracting total number of pixels - value pixels
    #     if axis == "Y":
    #         tot_label_diff = float(self.ylabels[-1] - label0)
    #         tot_label_whole = int(tot_label_diff / inc)
    #         tot_label_part = float(float(tot_label_diff / inc) - tot_label_whole)
    #         tot_label_pix = tot_label_whole * spacing + tot_label_part * spacing

    #         pixel = tot_label_pix - pixel

    #     # Add min edge pixels
    #     pixel = pixel + min

    #     if axis == "Y" and pixel > self.ymax:
    #         pixel = self.ymax

    #     return pixel

    # Print out which data point you just clicked on..
    def pickWhich(self, event):

        # Find closest data point
        x = event.widget.canvasx(event.x)
        y = event.widget.canvasx(event.y)
        spot = event.widget.find_closest(x, y)

        distance = math.sqrt( (self.coords(spot[0])[0] - x)*(self.coords(spot[0])[0] - x) + (self.coords(spot[0])[1] -y)*(self.coords(spot[0])[1] - y) ) 
        logging.debug("Distance of "+str(distance))

        # Print the shape's meta information corresponding with the shape that was picked
        if spot[0] in self.shapes and distance < 10:
            # self.picked = self.shapes[spot[0]][5][1]
            self.picked = spot[0]

    # Mouse Down Event
    def down(self, event):

        # Store x,y position
        self.lastx = event.x
        self.lasty = event.y

        # Find the currently selected item
        x = event.widget.canvasx(event.x)
        y = event.widget.canvasx(event.y)
        self.item = event.widget.find_closest(x, y)

        # Identify that the mouse is down
        self.isdown = 1

    # Mouse Up Event
    def up(self, event):

        # Get label space version of x,y
        labelx = self.convertToLabel("X", event.x)
        labely = self.convertToLabel("Y", event.y)

        # Convert new position into label space..
        if self.item[0] in self.shapes:
            self.shapes[self.item[0]][0] = event.x
            self.shapes[self.item[0]][1] = event.y
            self.shapes[self.item[0]][2] = 1
            self.shapes[self.item[0]][3] = labelx
            self.shapes[self.item[0]][4] = labely

        # Reset Flags
        self.item = (0,)
        self.isdown = 0

    # Mouse Drag(Move) Event
    def drag(self, event):

        # Check that mouse is down and item clicked is a valid data point
        if self.isdown and self.item[0] in self.shapes:

            self.move(self.item, event.x - self.lastx, event.y - self.lasty)

            self.lastx = event.x
            self.lasty = event.y


# def set_phipsi(model, index, phi, psi, state=-1):
#     atsele = [
#         'first ((%s`%d) extend 2 and name C)' % (model, index),  # prev C
#         'first ((%s`%d) extend 1 and name N)' % (model, index),  # this N
#         '(%s`%d)' % (model, index),                             # this CA
#         'last ((%s`%d) extend 1 and name C)' % (model, index),  # this C
#         'last ((%s`%d) extend 2 and name N)' % (model, index),  # next N
#     ]
#     try:
#         cmd.set_dihedral(atsele[0], atsele[1], atsele[2], atsele[3], phi, state)
#         cmd.set_dihedral(atsele[1], atsele[2], atsele[3], atsele[4], psi, state)
#     except:
#         print ' DynoPlot Error: cmd.set_dihedral failed'

# New Callback object, so that we can update the structure when phi,psi points are moved.

def check_selections(queue):
    """ Check if the selection made by the user changed """
    global previous_mouse_mode
    global myspace
    while True:
        # Check if the user changed the selection mode (atom/residue/chain/molecule)
        logging.debug("Current mouse selection mode : %d" % int(cmd.get("mouse_selection_mode")))
        logging.debug("Number of selections: %d" % len(cmd.get_names("selections")))
        if int(cmd.get("mouse_selection_mode")) == 5 and previous_mouse_mode == cmd.get("mouse_selection_mode") and len(cmd.get_names("selections")) >= 2:
            logging.info("--- Selection made by the user ---")
            logging.debug(cmd.get_names("selections")[1])
            if(cmd.get_names("selections")[1] == 'lb'):
                cmd.iterate('(lb)', 'models.add(model)', space=myspace)
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
        else:
            # if len(cmd.get_names("selections", enabled_only=1)) == 0:
            #     queue.put(set())
            previous_mouse_mode = cmd.get("mouse_selection_mode")
            time.sleep(1)


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

        self.canvas = 4*[]

        ###############################
        ##### NEW WINDOW FOR RMSD #####
        ###############################

        self.create_window(parent, 500, 500, 0, 50, 0, 0.27, symbols, Tkinter.LEFT, "Time Frame", "RMSD")


        if name is None:
            try:
                name = cmd.get_unused_name('Handler')
            except AttributeError:
                name = 'Handler'

        from rdflib import Graph

        self.rdf_graph = Graph()
        self.queue = queue
        self.rootframe = rootframe
        self.current_canvas = self.canvas[-1]
        self.name = name
        self.lock = 0
        self.state = state
        self.show = [False]*251
        self.models_to_display = set()
        self.all_models = set()
        self.models_shown = set()
        self.rdf_parsed = False

        reset = Tkinter.Button(self.rootframe, text = 'RESET', command = lambda: self.update_plot(2), anchor = "w")
        reset.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        reset_window = self.current_canvas.create_window(40, 490, anchor="sw", window=reset)

        select = Tkinter.Button(self.rootframe, text = 'SELECT FROM VIEWER', command = lambda: self.update_plot(3), anchor = "w")
        select.configure(width = 19, activebackground = "#33B5E5", relief = "raised")
        select_window = self.current_canvas.create_window(270, 490, anchor="se", window=select)

        self.current_canvas.create_line(40, 455, 300, 455, fill='black', width=1)

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

        ######
        # Command to select by dragging
        def onDrag(start, end, mode):
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
                        if x in self.canvas[0].shapes:
                            display.add(self.canvas[0].shapes[x][5][1])
                            # cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                            # cmd.show('line', '(sele)')
                            logging.debug(display)
                            self.show[self.canvas[0].shapes[x][5][1]-1] = True
                            locked = False
                self.update_plot_multiple(1, display, self.canvas[0])
                if len(display) == 0 and not locked:
                    self.update_plot_multiple(1, display, self.canvas[0])
                    locked = True
            elif mode == "all_in_one":
                logging.info("START/END: %d:%d / %d:%d" % (start[0], start[1], end[0], end[1]))
                x_low, x_high, y_low, y_high = self.canvas[0].convertToValues(start, end)
                logging.info("Value limits: x=[%f -> %f]\ny=[%f -> %f]" % (x_low, x_high, y_low, y_high))
                models_selected = self.query_sub_rdf(self.canvas[0], x_low, x_high, y_low, y_high)
                logging.info(models_selected)
                for model in models_selected:
                    self.show[model-1] = True
                self.update_plot_multiple(1, models_selected, self.canvas[0])
        #####
        rect.autodraw(fill="", width=1, command=onDrag)

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

        self.rootframe.after(500, self.update_plot_multiple)
        #####


        ######################################
        ##### NEW WINDOW FOR TEMPERATURE #####
        ######################################

        self.create_window(parent, 500, 500, 0, 50, 250, 320, symbols, Tkinter.LEFT, "Time Frame", "Temperature")

        #####
        # Call to selection tool
        rect2 = RectTracker(self.current_canvas)

        ######
        # Command to select by dragging
        def onDrag2(start, end, mode):
            global x,y, locked
            if mode == "update":
                items = rect2.hit_test(start, end)
                display=set()
                for x in rect2.items:
                    # if x not in items:
                    #     if x in canvas.shapes:
                    #         canvas.itemconfig(x, fill='grey')
                    #         if self.show[canvas.shapes[x][5][1]-1]:
                    #             cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                    #             cmd.hide('line', '(sele)')
                    # else:
                    if x in items:
                        #canvas.itemconfig(x, fill='blue')
                        if x in self.canvas[1].shapes:
                            display.add(self.canvas[1].shapes[x][5][1])
                            # cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                            # cmd.show('line', '(sele)')
                            logging.debug(display)
                            self.show[self.canvas[1].shapes[x][5][1]-1] = True
                            locked = False
                self.update_plot_multiple(1, display, self.canvas[1])
                if len(display) == 0 and not locked:
                    self.update_plot_multiple(1, display, self.canvas[1])
                    locked = True
            elif mode == "all_in_one":
                logging.info("START/END: %d:%d / %d:%d" % (start[0], start[1], end[0], end[1]))
                x_low, x_high, y_low, y_high = self.canvas[1].convertToValues(start, end)
                logging.info("Value limits: x=[%f -> %f]\ny=[%f -> %f]" % (x_low, x_high, y_low, y_high))
                models_selected = self.query_sub_rdf(self.canvas[1], x_low, x_high, y_low, y_high)
                logging.info(models_selected)
                for model in models_selected:
                    self.show[model-1] = True
                self.update_plot_multiple(1, models_selected, self.canvas[1])
        #####
        rect2.autodraw(fill="", width=1, command=onDrag2)
        

        delete2 = Tkinter.Button(self.rootframe, text = "Delete", command = lambda: self.delete(self.canvas[1]), anchor = "w")
        delete2.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        delete_window2 = self.current_canvas.create_window(210, 445, anchor="sw", window=delete2)


        #################################
        ##### NEW WINDOW FOR ENERGY #####
        #################################

        self.create_window(parent, 500, 500, 0, 50, 20000, 22800, symbols, Tkinter.LEFT, "Time Frame", "Energy")

        #####
        # Call to selection tool
        rect3 = RectTracker(self.current_canvas)

        ######
        # Command to select by dragging
        def onDrag3(start, end, mode):
            global x,y, locked
            if mode == "update":
                items = rect3.hit_test(start, end)
                display=set()
                for x in rect3.items:
                    # if x not in items:
                    #     if x in canvas.shapes:
                    #         canvas.itemconfig(x, fill='grey')
                    #         if self.show[canvas.shapes[x][5][1]-1]:
                    #             cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                    #             cmd.hide('line', '(sele)')
                    # else:
                    if x in items:
                        #canvas.itemconfig(x, fill='blue')
                        if x in self.canvas[2].shapes:
                            display.add(self.canvas[2].shapes[x][5][1])
                            # cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                            # cmd.show('line', '(sele)')
                            logging.debug(display)
                            self.show[self.canvas[2].shapes[x][5][1]-1] = True
                            locked = False
                self.update_plot_multiple(1, display, self.canvas[2])
                if len(display) == 0 and not locked:
                    self.update_plot_multiple(1, display, self.canvas[2])
                    locked = True
            elif mode == "all_in_one":
                logging.info("START/END: %d:%d / %d:%d" % (start[0], start[1], end[0], end[1]))
                x_low, x_high, y_low, y_high = self.canvas[2].convertToValues(start, end)
                logging.info("Value limits: x=[%f -> %f]\ny=[%f -> %f]" % (x_low, x_high, y_low, y_high))
                models_selected = self.query_sub_rdf(self.canvas[2], x_low, x_high, y_low, y_high)
                logging.info(models_selected)
                for model in models_selected:
                    self.show[model-1] = True
                self.update_plot_multiple(1, models_selected, self.canvas[2])
        rect3.autodraw(fill="", width=1, command=onDrag3)
        #####

        delete3 = Tkinter.Button(self.rootframe, text = "Delete", command = lambda: self.delete(self.canvas[2]), anchor = "w")
        delete3.configure(width = 6, activebackground = "#33B5E5", relief = "raised")
        delete_window3 = self.current_canvas.create_window(210, 445, anchor="sw", window=delete3)


        if selection is not None:
            self.start(selection, self.canvas[0], 'time_frame', 'RMSD')
            self.start(selection, self.canvas[1], 'time_frame', 'temperature')
            self.start(selection, self.canvas[2], 'time_frame', 'energy')

        if with_mainloop and pmgapp is None:
            rootframe.mainloop()

        #############################################
        ##### CREATE CANVAS ITEM IDs DICTIONARY #####
        #############################################
        self.create_ids_equivalent_dict()

        options = Canvas(parent, width=100, height=200)
        options.pack()

        model = Tkinter.Button(self.rootframe, text='MODEL', command = lambda: self.propose_analyses('MODEL'), anchor="w")
        model.configure(width=8, activebackground = "#FF0000", relief='raised')
        model_window = options.create_window(20, 20, anchor="n", window=model)


    def delete(self, canvas):
        print "Closed"
        self.canvas.remove(canvas)
        canvas.delete("all")
        canvas.pack()

    def create_ids_equivalent_dict(self):
        """ Create a dictionary of equivalent ids for each canvas created """
        for k,s in self.canvas[0].shapes.iteritems():
            self.canvas[0].ids_ext[k] = []
            for canv in self.canvas[1:]:
                for k1,s1 in canv.shapes.iteritems():
                    if s1[5][1] == s[5][1]:
                        self.canvas[0].ids_ext[k].append(k1)

        for i in range(1,len(self.canvas)):
            self.canvas[i].ids_ext = {v[i-1]: [item for sublist in [[k], v[:i-1], v[i:]] for item in sublist] for k,v in self.canvas[0].ids_ext.items()}

        logging.debug(self.canvas[0].shapes[192])
        logging.debug(self.canvas[1].shapes[self.canvas[0].ids_ext[192][0]])
        logging.debug(self.canvas[0].shapes[self.canvas[1].ids_ext[self.canvas[0].ids_ext[192][0]][0]])


    def update_plot_multiple(self, source =0, to_display=set(), canvas = None):
        """ Check for updated selections data in all plots simultaneously"""
        start_time = time.time()
        if canvas == None:
            canvas = self.current_canvas
        if source == 1:
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
                models = self.queue.get_nowait()
                logging.info("Models from user selection in the viewer: "+str(models))
                self.models_to_display = models.intersection(self.all_models)
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
                    for it in canvas.ids_ext[k]:
                        if self.canvas[cpt] != canvas:
                            self.canvas[cpt].itemconfig(it, fill='grey')
                        else:
                            cpt+=1
                            self.canvas[cpt].itemconfig(it, fill='grey')
                        cpt+=1
                    self.models_to_display.add(s[5][1])
                    self.models_shown.add(s[5][1])
            cmd.show('cartoon', 'name CA and all')

        logging.debug("---- %s seconds ----" % str(time.time()-start_time))
        self.rootframe.after(500, self.update_plot_multiple)

    def update_plot(self, source =0, to_display=set(), canvas=None):
        """ Check for updated selections data """
        start_time = time.time()
        if canvas == None:
            canvas = self.current_canvas

        if source == 1:
            logging.info("Display models sent by OnDrag: ")
            logging.info(to_display)
            self.models_to_display = to_display.intersection(self.all_models)
            logging.info(self.models_to_display)
            for k,s in canvas.shapes.iteritems():
                if s[5][1] in self.models_to_display and s[5][1] not in self.models_shown:
                    canvas.itemconfig(k, fill='blue')
                    logging.debug("Color: %04d" % s[5][1])
                    #cmd.select('sele', '%04d' % s[5][1])
                    cmd.show('line', '%04d' % s[5][1])
                    #cmd.disable('sele')
                elif s[5][1] not in self.models_to_display and s[5][1] in self.models_shown:
                    canvas.itemconfig(k, fill='grey')
                    logging.debug("Hide: %04d" % s[5][1])
                    #cmd.select('sele', '%04d' % s[5][1])
                    cmd.hide('line', '%04d' % s[5][1])
                    #cmd.disable('sele')
            self.models_shown = self.models_to_display  

        elif source == 0:
            # Check single picking items
            if canvas.picked != 0 and canvas.picked != canvas.previous:
                canvas.itemconfig(canvas.picked, fill='blue')
                cmd.select('sele', '%04d' % canvas.shapes[canvas.picked][5][1])
                cmd.show('line', '(sele)')
                logging.info("You selected item %d corresponding to model %d" % (k, s[5][1]))
                if canvas.previous != 0:
                    canvas.itemconfig(canvas.previous, fill='grey')
                    cmd.select('sele', '%04d' % canvas.shapes[canvas.previous][5][1])
                    cmd.hide('line', '(sele)')
                cmd.disable('sele')
                canvas.previous = canvas.picked
            # Check selection from PyMol viewer
            try:
                models = self.queue.get_nowait()
                logging.info("Models from user selection in the viewer: "+str(models))
                self.models_to_display = models.intersection(self.all_models)
                if len(self.models_to_display) > 0:
                    for k,s in canvas.shapes.iteritems():
                        if s[5][1] in self.models_to_display:
                            logging.info("Color red -> %04d" % s[5][1]) 
                            canvas.itemconfig(k, fill='blue')
                            cmd.color('red', '%04d' % s[5][1])
                        else:
                            logging.info("Color default -> %04d" % s[5][1]) 
                            canvas.itemconfig(k, fill='grey')
                            util.cbag('%04d' % s[5][1])
                            # cmd.select('sele', '%04d' % s[5][1])
                            # cmd.hide('line', '(sele)')
                            # cmd.disable('sele')
            except Queue.Empty:
                pass
        # Reset plot and viewer
        elif source == 2:
            logging.info("RESET")
            for canv in self.canvas:
                for k,s in canv.shapes.iteritems():
                    canv.itemconfig(k, fill='grey')
                    self.models_to_display.clear()
                    self.models_shown.clear()
            cmd.hide('line', 'all')
                
        # "Selection mode"
        elif source == 3:
            logging.info("SELECTION MODE")
            for canv in self.canvas:
                for k,s in canv.shapes.iteritems():
                    canv.itemconfig(k, fill='grey')
                    self.models_to_display.add(s[5][1])
                    self.models_shown.add(s[5][1])
            cmd.show('line', 'all')

        logging.debug("---- %s seconds ----" % str(time.time()-start_time))
        self.rootframe.after(1000, self.update_plot)


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



    def close_callback(self):
        cmd.delete(self.name)
        self.rootframe.destroy()

    def parse_rdf(self,filename):
        """ Parse the RDF database """
        start_time = time.time()

        logging.info("Parsing of %s..." % filename)
        self.rdf_graph.parse(filename, format="nt")
        logging.info ("---- %s seconds ----" % str(time.time()-start_time))
        logging.info("Number of triples: %d" % len(self.rdf_graph))

    def query_sub_rdf(self, canvas, xlow, xhigh, ylow, yhigh):
        """ Query the RDF graph for specific range of values made by user selection """
        from rdflib.plugins.sparql import prepareQuery
        query = 'SELECT ?id WHERE { ?point rdf:type my:point . ?point my:Y_type "'+str(canvas.y_query_type)+'" . ?point my:Y_value ?y . FILTER (?y > '+str(ylow)+' && ?y < '+str(yhigh)+') . ?point my:X_type "'+str(canvas.x_query_type)+'" . ?point my:X_value ?x . FILTER (?x > '+str(xlow)+' && ?x < '+str(xhigh)+') . ?point my:represent ?mod . ?mod my:model_id ?id .}'
        logging.info("QUERY: \n%s" % query)
        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres = self.rdf_graph.query(q)

        logging.info("Number of queried entities: %d " % len(qres))

        models = set()
        for row in qres:
            models.add(int(row[0]))

        return models

    def query_rdf(self, x_query_type, y_query_type):
        """ Query the RDF graph to build complete plot """
        from rdflib.plugins.sparql import prepareQuery
        query = 'SELECT ?x ?y ?id WHERE { ?point rdf:type my:point . ?point my:Y_type "'+y_query_type+'" . ?point my:Y_value ?y . ?point my:X_type "'+x_query_type+'" . ?point my:X_value ?x . ?point my:represent ?mod . ?mod my:model_id ?id .}'
        logging.info("QUERY: \n%s" % query)
        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres= self.rdf_graph.query(q)
        
        logging.info("Number of queried entities: %d " % len(qres))

        return qres

    def start(self, sel, canvas, x_query_type, y_query_type):
        self.lock = 1
        cmd.iterate('(%s) and name CA' % sel, 'idx2resn[model,index] = (resn, color, ss)',
                     space={'idx2resn': canvas.idx2resn})

        canvas.x_query_type = x_query_type
        canvas.y_query_type = y_query_type

        # Parse main RDF database
        if (not self.rdf_parsed):
            self.parse_rdf("/Users/trellet/Dev/Protege_OWL/data/all_parsed.ntriples")
            self.rdf_parsed = True
        # Query RMSD points to draw first plot
        qres = self.query_rdf(x_query_type, y_query_type)

        for row in qres:
            if int(row[2] not in self.all_models):
                self.all_models.add(int(row[2]))
            model_index = ('all', int(row[2]))
            canvas.plot(float(row[0]), float(row[1]), model_index)
        self.lock = 0

    # def start(self, sel):
    #     self.lock = 1
    #     cmd.iterate('(%s) and name CA' % sel, 'idx2resn[model,index] = (resn, color, ss)',
    #                  space={'idx2resn': self.canvas.idx2resn})
    #     import RDF
    #     import time

    #     parser=RDF.Parser(name="ntriples")
    #     model = RDF.Model()
    #     start_time = time.time()
    #     print start_time
    #     stream=parser.parse_into_model(model,"file://Users/trellet/Dev/Protege_OWL/data/pdb_rmsd.ntriples","http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
    #     print ("----%s seconds ----" % str(time.time()-start_time))

    #     self.lock = 0;

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
