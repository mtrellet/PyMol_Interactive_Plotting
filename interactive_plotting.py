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

# workaround: Set to True if nothing gets drawn on canvas, for example on linux with "pymol -x"
with_mainloop = False
# Global variables for pymol event checking
myspace = {'previous':set(), 'models':set()}
previous_mouse_mode = cmd.get("mouse_selection_mode")
locked = False


class PickWizard(Wizard):

    def __init__(self):
        self.sele_name = "lb" # must be set to "lb" for now...
        self.selected = []
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
        
        self._command = opts.pop('command', lambda *args: None)
        self.rectopts = opts
        
    def __update(self, event):
        if not self.start:
            self.start = [event.x, event.y]
            return
        
        if self.item is not None:
            self.canvas.delete(self.item)
        self.item = self.draw(self.start, (event.x, event.y), **self.rectopts)
        self._command(self.start, (event.x, event.y))
        
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

# def main():
#     from random import shuffle
    
#     canv = Canvas(width=500, height=500)
#     canv.create_rectangle(50, 50, 250, 150, fill='red')
#     canv.pack(fill=BOTH, expand=YES)
    
#     rect = RectTracker(canv)
#     # draw some base rectangles
#     rect.draw([50,50], [250, 150], fill='red', tags=('red', 'box'))
#     rect.draw([300,300], [400, 450], fill='green', tags=('gre', 'box'))
    
#     # just for fun
#     x, y = None, None
#     def cool_design(event):
#         global x, y
#         kill_xy()
        
#         dashes = [3, 2]
#         x = canv.create_line(event.x, 0, event.x, 1000, dash=dashes, tags='no')
#         y = canv.create_line(0, event.y, 1000, event.y, dash=dashes, tags='no')
        
#     def kill_xy(event=None):
#         canv.delete('no')
    
#     canv.bind('<Motion>', cool_design, '+')
    
#     # command
#     def onDrag(start, end):
#         global x,y
#         items = rect.hit_test(start, end)
#         for x in rect.items:
#             if x not in items:
#                 canv.itemconfig(x, fill='grey')
#                 print x
#             else:
#                 canv.itemconfig(x, fill='blue')
    
#     rect.autodraw(fill="", width=2, command=onDrag)
    
#     mainloop()


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
        self.lastx = 0      # previous x,y pos of mouse
        self.lasty = 0
        self.isdown = 0    # flag for mouse pressed
        self.item = (0,)    # items array used for clickable events
        self.shapes = {}    # store plot data, x,y etc..
        self.idx2resn = {}  # residue name mapping
        self.symbols = 0    # 0: amino acids, 1: secondary structure
        self.previous = 0   # Previous item selected
        self.picked = 0     # Item selected

    def axis(self, xmin=40, xmax=300, ymin=10, ymax=290, xint=290, yint=40, xlabels=[], ylabels=[]):

        # Store variables in self object
        self.xlabels = xlabels
        self.ylabels = ylabels
        self.spacingx = (xmax - xmin) / (len(xlabels) - 1)
        self.spacingy = (ymax - ymin) / (len(ylabels) - 1)
        self.xmin = xmin
        self.ymin = ymin

        # Create axis lines
        self.create_line((xmin, xint, xmax, xint), fill="black", width=3)
        self.create_line((yint, ymin, yint, ymax), fill="black", width=3)

        # Create tick marks and labels
        nextspot = xmin
        for label in xlabels:
            self.create_line((nextspot, xint + 5, nextspot, xint - 5), fill="black", width=2)
            self.create_text(nextspot, xint - 15, text=label)
            if len(xlabels) == 1:
                nextspot = xmax
            else:
                nextspot += (xmax - xmin) / (len(xlabels) - 1)

        nextspot = ymax
        for label in ylabels:
            self.create_line((yint + 5, nextspot, yint - 5, nextspot), fill="black", width=2)
            self.create_text(yint - 20, nextspot, text=label)
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
    def convertToPixel(self, axis, value):

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

        # Get axis increment in 'label' space
        inc = abs(label1 - label0)

        # 'Label' difference from value and smallest label (label0)
        diff = float(value - label0)

        # Get whole number in 'label' space
        whole = int(diff / inc)

        # Get fraction number in 'label' space
        part = float(float(diff / inc) - whole)

        # Return 'pixel' position value
        pixel = whole * spacing + part * spacing

        # Reverse number by subtracting total number of pixels - value pixels
        if axis == "Y":
            tot_label_diff = float(self.ylabels[-1] - label0)
            tot_label_whole = int(tot_label_diff / inc)
            tot_label_part = float(float(tot_label_diff / inc) - tot_label_whole)
            tot_label_pix = tot_label_whole * spacing + tot_label_part * spacing

            pixel = tot_label_pix - pixel

        # Add min edge pixels
        pixel = pixel + min

        return pixel

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
            # cmd.select('sele', '%04d' % self.shapes[spot[0]][5][1])
            # cmd.show('line','(sele)')
            # self.itemconfig(spot[0], fill='blue')
            # if self.previous != 0:
            #     self.itemconfig(self.previous, fill='grey')
            # self.previous = spot[0]
            # cmd.select('sele', '(%s`%d)' % self.shapes[spot[0]][5])
            # cmd.iterate('sele', 'print " You clicked /%s/%s/%s/%s`%s/%s (DynoPlot)" %' + \
            #             ' (model, segi, chain, resn, resi, name)')
            # cmd.center('byres sele', animate=1)

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


class DynoRamaObject:

    def __init__(self, queue, selection=None, name=None, symbols='', state=-1):
        from pymol import _ext_gui as pmgapp
        if pmgapp is not None:
            import Pmw
            rootframe = Pmw.MegaToplevel(pmgapp.root)
            parent = rootframe.interior()
        else:
            rootframe = Tkinter.Tk()
            parent = rootframe

        rootframe.title(' Interactive Analyses ')
        rootframe.protocol("WM_DELETE_WINDOW", self.close_callback)

        self.canvas = 4*[]

        self.create_window(parent, 500, 500, 0, 50, 0, 0.27, symbols)


        if name is None:
            try:
                name = cmd.get_unused_name('DynoRama')
            except AttributeError:
                name = 'DynoRamaObject'

        self.queue = queue
        self.rootframe = rootframe
        self.current_canvas = self.canvas[-1]
        self.name = name
        self.lock = 0
        self.state = state
        self.show = [False]*251
        self.models_to_display = set()
        self.all_models = set()
        
        if name != 'none':
            auto_zoom = cmd.get('auto_zoom')
            cmd.set('auto_zoom', 0)
            cmd.load_callback(self, name)
            cmd.set('auto_zoom', auto_zoom)
            # canvas.bind("<ButtonPress-1>", canvas.down)
            # canvas.bind("<ButtonRelease-1>", canvas.up)
            # canvas.bind("<Motion>", canvas.drag)

        #######################################################################
        # Call to selection tool
        rect = RectTracker(self.current_canvas)

        # command
        def onDrag(start, end):
            global x,y, locked
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
                    if x in self.current_canvas.shapes:
                        display.add(self.current_canvas.shapes[x][5][1])
                        # cmd.select('sele', '%04d' % canvas.shapes[x][5][1])
                        # cmd.show('line', '(sele)')
                        self.show[self.current_canvas.shapes[x][5][1]-1] = True
                        self.update_plot(1, display)
                        locked = False
            if len(display) == 0 and not locked:
                self.update_plot(1, display)
                locked = True
        rect.autodraw(fill="", width=2, command=onDrag)
        #######################################################################

        #######################################################################
        # Call to wizard tool
        wiz = PickWizard()

        # make this the active wizard

        cmd.set_wizard(wiz)

        # wiz.register_observer(self.notify)
        # wiz.notify_observers('test')

        self.rootframe.after(1000, self.update_plot)
        #######################################################################


        if selection is not None:
            self.start(selection)

        if with_mainloop and pmgapp is None:
            rootframe.mainloop()

    def update_plot(self, source =0, to_display=set()):
        """ Check for updated selections data """
        if source == 1:
            logging.info("Display models sent by OnDrag: ")
            logging.info(to_display)
            self.models_to_display = to_display.intersection(self.all_models)
            logging.info(self.models_to_display)
            for k,s in self.current_canvas.shapes.iteritems():
                if s[5][1] in self.models_to_display:
                    self.current_canvas.itemconfig(k, fill='blue')
                    cmd.select('sele', '%04d' % s[5][1])
                    cmd.show('line', '(sele)')
                    cmd.disable('sele')
                else:
                    self.current_canvas.itemconfig(k, fill='grey')
                    cmd.select('sele', '%04d' % s[5][1])
                    cmd.hide('line', '(sele)')
                    cmd.disable('sele')
        
        elif source == 0:
            # Check single picking items
            if self.current_canvas.picked != 0 and self.current_canvas.picked != self.current_canvas.previous:
                self.current_canvas.itemconfig(self.current_canvas.picked, fill='blue')
                cmd.select('sele', '%04d' % self.current_canvas.shapes[self.current_canvas.picked][5][1])
                cmd.show('line', '(sele)')
                if self.current_canvas.previous != 0:
                    self.current_canvas.itemconfig(self.current_canvas.previous, fill='grey')
                    cmd.select('sele', '%04d' % self.current_canvas.shapes[self.current_canvas.previous][5][1])
                    cmd.hide('line', '(sele)')
                cmd.disable('sele')
                self.current_canvas.previous = self.current_canvas.picked
            # Check selection from PyMol viewer
            try:
                models = self.queue.get_nowait()
                logging.info("Models from user selection in the viewer: "+str(models))
                self.models_to_display = models.intersection(self.all_models)
                if len(self.models_to_display) > 0:
                    for k,s in self.current_canvas.shapes.iteritems():
                        if s[5][1] in self.models_to_display:
                            logging.info("Color red -> %04d" % s[5][1]) 
                            self.current_canvas.itemconfig(k, fill='blue')
                            cmd.color('red', '%04d' % s[5][1])
                        else:
                            logging.info("Color default -> %04d" % s[5][1]) 
                            self.current_canvas.itemconfig(k, fill='grey')
                            util.cbag('%04d' % s[5][1])
                            # cmd.select('sele', '%04d' % s[5][1])
                            # cmd.hide('line', '(sele)')
                            # cmd.disable('sele')
            except Queue.Empty:
                pass
        self.rootframe.after(1000, self.update_plot)


    # def notify(self, observable, *args, **kwargs):
    #     print('Got', args, kwargs, 'From', observable)
    #     myspace = {'models':[]}
    #     cmd.iterate('(lb)', 'models.append(model)', space=myspace)
    #     for i in set(myspace['models']):
    #         if int(i) not in self.models_to_display:
    #             self.models_to_display.add(int(i))
    #     for m in self.models_to_display:
    #         for s in self.canvas.shapes:
    #             if m == self.canvas.shapes[s][5][1]:
    #                 self.canvas.itemconfig(s, fill='blue')

    def create_window(self, parent, width, height, min_x, max_x, min_y, max_y, symbols):
        """ Create new plot window """
        canvas = SimplePlot(parent, width=width, height=height)
        #canvas.bind("<Button-2>", canvas.pickWhich)
        canvas.bind("<ButtonPress-3>", canvas.pickWhich)
        canvas.pack(side=Tkinter.LEFT, fill="both", expand=1)
        x_gap = float(max_x-min_x) / 5
        y_gap = float(max_y - min_y) / 5
        xlabels = [float("{0:.2f}".format(min_x + i*x_gap)) for i in range(6)]
        ylabels = [float("{0:.2f}".format(min_y + i*y_gap)) for i in range(6)]
        canvas.axis(xlabels=xlabels,
                    ylabels=ylabels)
        canvas.update()

        if symbols == 'ss':
            canvas.symbols = 1

        self.current_canvas = canvas
        self.canvas.append(canvas)



    def close_callback(self):
        cmd.delete(self.name)
        self.rootframe.destroy()

    # def start(self, sel):
    #     self.lock = 1
    #     cmd.iterate('(%s) and name CA' % sel, 'idx2resn[model,index] = (resn, color, ss)',
    #                 space={'idx2resn': self.canvas.idx2resn})
    #     for model_index, (phi, psi) in cmd.get_phipsi(sel, self.state).iteritems():
    #         #print " Plotting Phi,Psi: %8.2f,%8.2f" % (phi, psi)
    #         self.canvas.plot(phi, psi, model_index)
    #     self.lock = 0

    def start(self, sel):
        self.lock = 1
        cmd.iterate('(%s) and name CA' % sel, 'idx2resn[model,index] = (resn, color, ss)',
                     space={'idx2resn': self.current_canvas.idx2resn})
        from rdflib import Graph
        from rdflib.plugins.sparql import prepareQuery
        import time
        g=Graph()
        start_time = time.time()
        filename = "/Users/trellet/Dev/Protege_OWL/data/tmp.ntriples"
        logging.info("Parsing of %s..." % filename)
        g.parse(filename, format="nt")
        logging.info ("---- %s seconds ----" % str(time.time()-start_time))
        logging.info("Number of triples: %d" % len(g))
        q = prepareQuery(
        'SELECT ?x ?y ?id  WHERE { ?point rdf:type my:point . ?point my:Y_value ?y . ?point my:represent ?mod . ?mod my:time_frame ?x . ?mod my:model_id ?id .}', initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres= g.query(q)
        
        logging.info("Number of queried entities: %d " % len(qres))

        for row in qres:
            self.all_models.add(int(row[2]))
            model_index = ('all', int(row[2]))
            self.current_canvas.plot(float(row[0]), float(row[1]), model_index)
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
    object {default: DynoRamaObject}

    symbols = string: aa for amino acid or ss for secondary structure {default: aa}

    filename = string: filename for postscript dump of canvas {default: None}
    '''
    queue = Queue.Queue()
    # Start background thread to check selections
    t = threading.Thread(target=check_selections, args=(queue,))
    t.start()
    logging.info("Checking changes in selections... (infinite loop)")
    dyno = DynoRamaObject(queue, sel, name, symbols, int(state))
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
                             command=lambda: DynoRamaObject(queue, '(enabled)'))

# vi:expandtab:smarttab
