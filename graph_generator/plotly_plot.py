import Tkinter
from Tkinter import BooleanVar
import math

import logging
logging.basicConfig(filename='pymol_session.log',filemode='w',level=logging.INFO)

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
        self.selected = [] # models selected in the canvas

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
        unit_per_pixel_x = float(abs(float(self.xlabels[-1])-float(self.xlabels[0]))/abs(float(self.xmax)-float(self.xmin)))
        unit_per_pixel_y = float(abs(float(self.ylabels[-1])-float(self.ylabels[0]))/abs(float(self.ymax)-float(self.ymin)))

        # logging.info("xlabels: %f %f / ylabels: %f %f", (self.xlabels[0], self.xlabels[-1], self.ylabels[0], self.ylabels[-1]))
        print self.xlabels
        print self.ylabels
        print self.xmin, self.xmax, self.ymin, self.ymax

        logging.info("Px/unit X: %f / Y: %f" % (unit_per_pixel_x, unit_per_pixel_y))

        x_low = self.xlabels[0]+(start[0]-self.xmin) * unit_per_pixel_x
        x_high = self.xlabels[0]+(end[0]-self.xmin) * unit_per_pixel_x
        y_low = self.ylabels[0]+(self.ymax-start[1]) * unit_per_pixel_y
        y_high = self.ylabels[0]+(self.ymax-end[1]) * unit_per_pixel_y

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
        pixel_per_unit_x = float(abs(float(self.xmax)-float(self.xmin))/abs(float(self.xlabels[-1])-float(self.xlabels[0])))
        pixel_per_unit_y = float(abs(float(self.ymax)-float(self.ymin))/abs(float(self.ylabels[-1])-float(self.ylabels[0])))

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
        logging.info("Distance of "+str(distance))

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