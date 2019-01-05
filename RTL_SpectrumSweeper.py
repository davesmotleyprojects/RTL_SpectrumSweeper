#!/usr/bin/env python3
"""
/* ######################################################################### */
/*
    RTL_SpectrumSweeper.py

    This program provides a GUI front-end for rtl_power.  

    Copyright 2018 David Hunt (www.DavesMotleyProjects.com)

    Permission is hereby granted, free of charge, to any person obtaining a 
    copy of this software and associated documentation files (the "Software"), 
    to deal in the Software without restriction, including without limitation 
    the rights to use, copy, modify, merge, publish, distribute, sublicense, 
    and/or sell copies of the Software, and to permit persons to whom the 
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included 
    in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS 
    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY 
    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
    SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    
 *                                                                           */
/* ######################################################################### */
"""

import os
import sys
import time
import subprocess
import datetime

import PIL.Image as Image

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation

import numpy as np
import tkinter as tk


version = '1.1.0'

###############################################################################
#                                                                             #
#   RELEASE NOTES                                                             #
#                                                                             #
###############################################################################

"""############################################################################

    Version 1.0.0: (20181229) Initial release.
    Version 1.1.0: (20190105) Added a debug section to add args as though it
    was executed from a command prompt when debugging with an IDE. Added an
    automatic file downloader for heatmap.py and flatten.py, and removed
    them from the git location to avoid duplication. Added support for 
    custom palettes (--palette and --rgbxy). Fixed automation interval to use
    milliseconds not seconds. Added check to avoid processing csv file if it
    has not changed since last update.  

############################################################################"""

print("\nRTL_SpectrumScanner.py version {}\n" .format(version))



"""############################################################################

    IDE Test Strings
    
    Uncomment this section to be able to execute/debug within an IDE like geany.
    The "cmd_str" will be parsed into sys.args as though they were input from
    the command line. DO NOT FORGET to comment this back out when done.  

############################################################################"""

'''
# here are some color codes for reference. copy these into a cmd_str to use. 
# '--palette custom'                                # default: BRIGHT YELLOW
# '--palette custom --rgbxy 0 255 255 15 140'       # CYAN
# '--palette custom --rgbxy 127 255 212 15 110'     # AQUAMARINE
# '--palette custom --rgbxy 255 20 147 10 110'      # HOT_PINK
# '--palette custom --rgbxy 160 32 240 0 110'       # DEEP_PURPLE
# '--palette custom --rgbxy 0 255 127 10 140'       # SPRING_GREEN

# some rtl_power settings for reference
# '-i 3s -e 60m -g 28 -f 88M:108M:5k test.csv'      # 1 hours scan of FM Stations 
# '-i 3s -g 28 -f 95000k:97500k:1k test.csv'        # hi-res scan of FM portion 
# '-i 1m -g 28 -f 27M:1000M:1M test.csv'            # scan of the rtl-sdr range up to 1GHz
# '-i 3s -g 28 -f 132000k:132200k:100 test.csv'     # scan of entire 40m ham band 


#cmd_str = "RTL_SpectrumSweeper -a 75 -s 15 --palette custom -i 3s -e 60m -g 28 -f 88M:108M:5k test.csv"  
cmd_str = "RTL_SpectrumSweeper -a 101 -s 101 --palette charolastra -c 25% -i 3s -g 28 -f 88M:108M:10k test.csv"         
#cmd_str = "RTL_SpectrumSweeper -a 101 -s 101 --palette custom --rgbxy 0 255 255 25 150 -c 25% -i 3s -e 60m -g 28 -f 88M:108M:10k test.csv"        
#cmd_str = "RTL_SpectrumSweeper -a 200 -s 100 -i 3s -e 60m -g 28 -f 88M:108M:5k test.csv" 

print(cmd_str)
sys.argv = cmd_str.split()
'''


"""############################################################################

    Confirm and if needed Download Required Files

############################################################################"""

heatmap_url = "https://github.com/davesmotleyprojects/rtl-sdr-misc/raw/master/heatmap/heatmap.py"
heatmap_path = os.path.join(sys.path[0], "heatmap.py")
flatten_url = "https://github.com/davesmotleyprojects/rtl-sdr-misc/raw/master/heatmap/flatten.py"
flatten_path = os.path.join(sys.path[0], "flatten.py")

urlretrieve = lambda a, b: None
try:
    import urllib.request
    urlretrieve = urllib.request.urlretrieve
except:
    import urllib
    urlretrieve = urllib.urlretrieve
    
if not os.path.isfile(heatmap_path):
    print('\nUnable to locate heatmap.py file at {}' .format(heatmap_path))
    try:
        print('Attempting to download it from {}' .format(heatmap_url))
        urlretrieve(heatmap_url, heatmap_path)
        print('Download successful')
    except Exception as e:
        print('Exception occurred while attempting download.\n{}\n' .format(e))
        print('Please download heatmap.py and place it in the current directory.')
        sys.exit(1)
        
if not os.path.isfile(flatten_path):
    print('\nUnable to locate flatten.py file at {}' .format(flatten_path))
    try:
        print('Attempting to download it from {}' .format(flatten_url))
        urlretrieve(flatten_url, flatten_path)
        print('Download successful')
    except Exception as e:
        print('Exception occurred while attempting download.\n{}\n' .format(e))
        print('Please download flatten.py and place it in the current directory.')
        sys.exit(1)


"""############################################################################

    Global Variables

############################################################################"""

class global_vars:
    
    def __init__(self):

        self.filename = ""
        self.sweeptime = 3

        self.opt_str = ""
        self.rtl_str = ""
        self.hmp_str = ""
        
        self.stop = 1       # 0 = autostop disabled
                            # 1 = autostop when window filled
                            # N = autostop when N sweeps completed
        self.aspect = 1     # 0 = stretch/shrink window to fill display
                            # 1 = force image aspect ratio to window
                            # N = force waterfall to N pixel height
        self.offset = 0
        
        self.trace_color = "#FFFF00"

        self.ready = False
        self.done = False
        
        self.csv_path = ""
        self.old_csv_size = 0

        root = tk.Tk()
        self.scrn_width_in = root.winfo_screenmmwidth() / 25.4
        self.scrn_height_in = root.winfo_screenmmheight() / 25.4

        self.combined_image = None
        self.tmax = 0.0

        self.fig_title = ""
        self.rows = 3
        self.fig = None
        self.ax1 = None
        self.ax2 = None

        self.ax1_w = 0
        self.ax1_h = 0
        self.ax2_w = 0
        self.ax2_h = 0

        self.rtl_proc = None

        self.anim = None 
        self.anim_intvl = self.sweeptime * 1000

        self.x_vals = []
        self.y_vals = []
        
        
print("\nInitializing global variables... ", end='', flush=True)   
g = global_vars()
print("done")


"""############################################################################

    function:   process_args 

############################################################################"""

def process_args():
    
    print("\nProcessing arg list")
    
    print("num args {}" .format(len(sys.argv)))
    print("arg list: {}" .format(str(sys.argv)))
        
    skip = 0
    g.opt_str = ""
    g.rtl_str = "rtl_power -P"
    g.hmp_str = "python heatmap.py --nolabels"
    
    
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if (skip):
            skip -= 1
        else:
            if (arg == "-s"):
                g.opt_str += str(" -s " + sys.argv[i+1])
                g.stop = int(sys.argv[i+1])
                print("Set stop: {}" .format(g.stop))
                skip=1
                pass
            elif (arg == "-a"):
                g.opt_str += str(" -a " + sys.argv[i+1])
                g.aspect = int(sys.argv[i+1])
                print("Set aspect: {}" .format(g.aspect))
                skip=1
                pass
            elif (arg == "-o"):
                g.opt_str += str(" -o " + sys.argv[i+1])
                g.offset = float(sys.argv[i+1])
                print("Set offset: {}" .format(g.offset))
                skip=1
                pass
            elif (arg == "--palette"):
                g.hmp_str += str(" --palette " + sys.argv[i+1])
                skip=1
                pass
            elif (arg == "--rgbxy"):
                R = int(sys.argv[i+1]); G = int(sys.argv[i+2]); B = int(sys.argv[i+3]);
                g.hmp_str += str(" --rgbxy " + sys.argv[i+1])
                g.hmp_str += str(" " + sys.argv[i+2])
                g.hmp_str += str(" " + sys.argv[i+3])
                g.hmp_str += str(" " + sys.argv[i+4])
                g.hmp_str += str(" " + sys.argv[i+5])
                g.trace_color = ("#{:02X}{:02X}{:02X}" .format(R,G,B))
                print("Trace Color: {}" .format(g.trace_color))
                skip=5
                pass
            elif (arg == "-P"):
                #do nothing. This is always added by default
                pass
            else:
                if(arg.find('.csv') != -1):
                    g.csv_path = os.path.join(sys.path[0], arg)
                    g.filename = arg.strip('.csv')
                    print("Filename is {}.csv" .format(g.filename))
                if(arg == "-i"):
                    g.sweeptime = duration_parse(sys.argv[i+1])
                    print("Sweep time is {} seconds" .format(g.sweeptime))
                    arg += str(" " + sys.argv[i+1])
                    skip=True
                g.rtl_str += str(" " + arg)
                
    print("\n")
    print("options = '{} {}'" .format(g.opt_str, g.hmp_str))
    print("{}" .format(g.rtl_str))
        
    time.sleep(3)


"""############################################################################

    function:   start_rtl_power_process 

############################################################################"""

def duration_parse(s):
    suffix = 1
    if s.lower().endswith('s'):
        suffix = 1
    if s.lower().endswith('m'):
        suffix = 60
    if s.lower().endswith('h'):
        suffix = 60 * 60
    if s.lower().endswith('d'):
        suffix = 24 * 60 * 60
    if suffix != 1 or s.lower().endswith('s'):
        s = s[:-1]
    return float(s) * suffix


"""############################################################################

    function:   start_rtl_power_process 

############################################################################"""

def start_rtl_power_process():
    
    print("\nStarting rtl_power subprocess\n")
        
    try:
        
        '''#####################################################################
        IMPORTANT: There is a problem with rtl_power that will occassionally 
        (or frequently, depending on settings) put "nan" in the csv file. 
        This causes the heatmap.py to fail. 
        Always using the '-P' option fixes this problem. 
        #####################################################################'''
         
        print(g.rtl_str)
        cmd = g.rtl_str.split()
        print(cmd)
        
        g.fig_title = ("RTL_SpectrumSweeper using: '{} {}' for '{}' started {}" .format(g.opt_str, g.hmp_str, g.rtl_str, datetime.datetime.now()))

        g.rtl_proc = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

        while(True):
            rspn = (str(g.rtl_proc.stdout.readline()))
            if (rspn[2:-5] == "[R82XX] PLL not locked!"):
                print(rspn[2:-5])
                break
            elif (rspn == "b''"):
                print(rspn)
                break
            else:
                print(rspn[2:-5])
        
        print("done")
    
    except Exception as e:
        
        print("\nException occurred in start_rtl_power_process")
        print(e)
        
        
"""############################################################################

    function:   wait_for_initial_data 

############################################################################"""

def wait_for_initial_data():
    
    print("\nWaiting for initial data ready")
    
    try:
        
        while(True):
            time.sleep(1)
            update_csv_data()
            #update_waterfall()
            update_spectrum()
            if (len(g.y_vals) > 0):
                g.ready = True
                print("Ready!")
                break
        
    except Exception as e:
        
        print("\nException occurred in wait_for_initial_data")
        print(e)
        

"""############################################################################

    function:   Initialize_plot 

############################################################################"""

def initialize_plot():
    
    print("\nInitializing plot... ", end='', flush=True)
    
    try:
        
        # use tk to get the screen size, and set the plot window to be just 
        # under the screen size. Note: The reading and setting of display 
        # sizes on Win10 has not been straightforward. This seems to be 
        # partly due to dpi scaling on my PC, but other values e.g. from 
        # get_window_extent don't seem to be correct at all. This needs 
        # further investigation. 
           
        root = tk.Tk()
        g.scrn_width_in = root.winfo_screenmmwidth() / 25.4
        g.scrn_height_in = root.winfo_screenmmheight() / 25.4
        plt.rcParams["figure.figsize"] = [g.scrn_width_in, 
                                          g.scrn_height_in*0.9]
        #plt.axis('off')
        #plt.margins(0)
        #plt.tight_layout()
        
        g.fig = plt.figure(g.fig_title)
        gs = gridspec.GridSpec(g.rows, 1, figure=g.fig)
        g.ax1 = g.fig.add_subplot(gs[0,0])
        g.ax2 = g.fig.add_subplot(gs[1:,0])
        
        g.ax1.margins(0)
        g.ax2.margins(0)
        g.ax1.set_facecolor('#000000')
        g.ax2.set_facecolor('#000000')
        #g.ax1.set_axis_off()
        #g.ax2.set_axis_off()
        g.ax1.set_aspect('auto')
        g.ax2.set_aspect('auto')
        g.fig.canvas.draw()

        
        bbox = g.ax2.get_window_extent().transformed(g.fig.dpi_scale_trans.inverted())
        g.ax2_w, g.ax2_h = int(bbox.width*g.fig.dpi), int(bbox.height*g.fig.dpi)
        bgnd = Image.new("RGB",(g.ax2_w,g.ax2_h),'#000000') 
        g.ax2.imshow(bgnd)
        
        #print("ax2 window size: width={}, height={}" .format(g.ax2_w, g.ax2_h))
        #print("bgnd2 image size: width={}, height={}" .format(bg2.size[0],bg2.size[1]))
        
        
        # This is the same code that gets executed by the animation
        g.ax1.clear()
        g.ax1.plot(g.x_vals, g.y_vals, color='yellow', linewidth=0.75) 
        y_min = min(g.y_vals); y_max = max(g.y_vals)
        y_diff = y_max-y_min; y_margin = y_diff *0.10
        g.ax1.set_ylim([min(g.y_vals)-y_margin, max(g.y_vals)+y_margin])
        #g.ax1.set_xlim([0, len(g.x_vals)])
        g.ax1.set_xlim([g.x_vals[0], g.x_vals[-1]])
        g.fig.canvas.draw()
                
        print("done")
        
    except Exception as e:
        
        print("\nException occurred in initialize_plot")
        print(e)
        
        
"""############################################################################

    function:   animation_poll 

############################################################################"""

def animation_poll(i):

    print("\nStarted animation poll at {}" .format(datetime.datetime.now()))
            
    try:
        
        # execute this code only while the rtl_power process is running.
        # while it is running the poll will return None. 
        if (g.rtl_proc.poll() == None):
            
            cur_csv_size = os.path.getsize(g.csv_path)
            if (g.old_csv_size == cur_csv_size):
                print("no new data to process yet. Exiting.")
                return

            g.old_csv_size = cur_csv_size
        
            update_csv_data()
            
            update_waterfall()
            
            try:
                g.ax2.imshow(g.combined_image)
                g.ax2.set_aspect('auto')
                #g.ax2.set_axis_off()
                #g.ax2.set_ylim([g.tmax, 0])
                g.ax2.set_xlabel("FFT Bins (N)")
                g.ax2.set_ylabel("Spectrum Sweeps (N)")
                plt.tight_layout()
                g.fig.canvas.draw()
            except:
                pass
                
            update_spectrum()
            
            try:
                g.ax1.clear()
                g.ax1.plot(g.x_vals, g.y_vals, color=g.trace_color, linewidth=0.75) 
                y_min = min(g.y_vals); y_max = max(g.y_vals)
                y_diff = y_max-y_min; y_margin = y_diff *0.10
                g.ax1.set_ylim([min(g.y_vals)-y_margin, max(g.y_vals)+y_margin])
                #g.ax1.set_xlim([0, len(g.x_vals)])
                g.ax1.set_xlim([g.x_vals[0], g.x_vals[-1]])
                g.ax1.set_xlabel("Frequency (MHz)")
                g.ax1.set_ylabel("Power (dB)")
                plt.tight_layout()
                g.fig.canvas.draw()
            except:
                pass
            
            print("Finished animation poll at {}" .format(datetime.datetime.now()))

            
            if(g.done):
                print("\nauto-stop criteria was met.")
                # stop the animation polling. 
                g.anim.event_source.stop()
                g.rtl_proc.terminate()
                print("The rtl_power subprocess was terminated.")
                    
        else:
            print("rtl_power subprocess finished!")
            # stop the animation polling. 
            g.anim.event_source.stop()

    except Exception as e:
        
        print("\nException occurred in animation_poll")
        print(e)
        
 

"""############################################################################

    function:   update_csv_data 

############################################################################"""

def update_csv_data():
    
    print("Updating csv data")
    
    try:
        cmd_str = ("{} {}.csv {}.png" .format(g.hmp_str, g.filename, g.filename)) 
        cmd = cmd_str.split()
        #print(cmd)

        proc = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        
        while(True):
            rspn = (str(proc.stdout.readline()))
            if (rspn == "b''"):
                #print("done")
                break
            else:
                #print(rspn[2:-5])
                if (rspn == ""):
                    print("RTL_SpectrumSweeper requires a version of heatmap.py that supports")
                    print("the --nolabels option. Copy the correct version from this location:")
                    print("https://github.com/davesmotleyprojects/rtl-sdr-misc/tree/master/heatmap")
                    print("into the directory with RTL_SpectrumSweeper.py and try again.")
                    sys.exit()
                pass
        
    except Exception as e:
        
        print("\nException occurred in update_csv_data")
        print(e)

    finally:
        
        proc.terminate()


"""############################################################################

    function:   update_waterfall 

############################################################################"""
    
def update_waterfall():
    
    print("Updating waterfall")
    
    try:
        
        fstr = ("{}.png" .format(g.filename))
        #print("opening: {}" .format(fstr))
        img1 = Image.open(fstr)
        #print("opened image file")
        w1,h1 = img1.size
        print("image size: width={}, height={}" .format(w1,h1))
        #print("ax2 window size: width={}, height={}" .format(g.ax2_w, g.ax2_h))
        
        wpcnt = (g.ax2_w / float(w1))   
        h2size = int((float(g.ax2_h)/float(wpcnt))-h1)
        
        #print("wpcnt={}, h2size={}" .format(wpcnt, h2size))
        #print("Remaining window size = {}" .format(h2size))
        
        
        '''
        self.stop = 0       # 0 = autostop disabled
                            # 1 = autostop when window filled
                            # N = autostop when N sweeps completed
        self.aspect = 0     # 0 = stretch/shrink window to fill display
                            # 1 = force image aspect ratio to window
                            # N = force waterfall to N pixel height
        '''
        
        
        # if g.stop == 0 (disabled)
        if (0 == g.stop):
            pass # do nothing
    
        # if g.stop == 1 (stop when window filled)
        elif (1 == g.stop):
            print("auto-stopping in {} sweeps" .format(h2size))
            # and the window is full
            if (h2size <= 0):
                g.done = True  
        
        # if g.stop == N (stop after N sweeps)
        else:
            # and the waterfal is more than N pixels high
            print("auto-stopping in {} sweeps" .format(g.stop-h1))
            if (h1 >= g.stop):
                g.done = True
            

        if (0 == g.aspect):
            #print("using unmodified heatmap image")
            g.combined_image = img1
            g.tmax = h1
                
        elif ((1 == g.aspect) and (h2size > 0)):
            bg2 = Image.new("RGB",(w1,h2size),'#000000') 
            w,h = bg2.size
            #print("bgnd2 image size: width={}, height={}" .format(w,h))
            g.combined_image = np.concatenate((img1, bg2), axis = 0)
            w,h = g.combined_image.shape[1], g.combined_image.shape[0]
            #print("combined image size: width={}, height={}" .format(w,h))
            g.tmax = h 
        
        else:
            if ((g.aspect-h1) > 0):
                bg2 = Image.new("RGB",(w1,g.aspect-h1),'#000000') 
                w,h = bg2.size
                #print("bgnd2 image size: width={}, height={}" .format(w,h))
                g.combined_image = np.concatenate((img1, bg2), axis = 0)
                w,h = g.combined_image.shape[1], g.combined_image.shape[0]
                #print("combined image size: width={}, height={}" .format(w,h))
                g.tmax = h
            else:
                #print("using unmodified heatmap image")
                g.combined_image = img1
                g.tmax = h1

        #print("done")
        
    except Exception as e:
        
        print("\nException occurred in update_waterfall")
        print(e)
    

"""############################################################################

    function:   update_spectrum 

############################################################################"""

def update_spectrum():
    
    print("Updating spectrum")
    
    try:
        
        cmd_str = ("python flatten.py {}.csv" .format(g.filename)) 
        cmd = cmd_str.split()
        #print(cmd)

        proc = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        
        g.x_vals = []; g.y_vals = []; 
        
        while(True):
            rspn = (str(proc.stdout.readline()))
            if (rspn == "b''"):
                #print("done")
                break
            else:
                g.x_vals.append(float((rspn[2:-5]).split(",")[0]))
                g.y_vals.append(float((rspn[2:-5]).split(",")[1]))
                g.x_vals[-1] += g.offset
                g.x_vals[-1] /= 1000000.0
                #print(g.x_vals[-1], g.y_vals[-1])

        #print("size of y_vals[] = {}" .format(len(g.y_vals)))
        
    except Exception as e:
        
        print("\nException occurred in update_spectrum")
        print(e)

    finally:
        
        proc.terminate()
        

"""############################################################################

    function:   main 

############################################################################"""

def main():
    
    try:
    
        process_args()
        start_rtl_power_process()
        wait_for_initial_data()
        initialize_plot()
        g.anim = animation.FuncAnimation(g.fig, animation_poll, interval=g.anim_intvl)
        plt.tight_layout()
        
        print("\nRunning... ", end='', flush=True)
        plt.show() 
        print("done")
        
    except Exception as e:
        
        print("\nException occurred in main")
        print(e)
    
    finally:
        
        print("\nrtl_scan Finished!")
        try:
            g.rtl_proc.terminate()
        except:
            pass


"""############################################################################

    This section checks whether the file is being executed directly, or if it
    is being imported by another module. 

############################################################################"""

if __name__ == '__main__':
    main()
