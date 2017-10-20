# -*- coding: utf-8 -*-
"""
Created on Fri Oct  6 15:09:43 2017

@author: dmdopc
"""

import sys, os
import numpy as np
import cv2
import copy
from pyicic.IC_ImagingControl import *
import time
import threading

class ISCam(object):
    def __init__(self,t_exp=0.01,bitdepth=8,windowwidthpx=1000):
        self.t_exp = t_exp
        self.bitdepth = bitdepth
        self.windowwidthpx = windowwidthpx

    def preview(self,t_exp=None,bitdepth=None,displaythresh=None):
        t_exp = t_exp or self.t_exp
        bitdepth = bitdepth or self.bitdepth
        self._previewThread = threading.Thread(name='tis_preview',target=self._previewCam,kwargs={'t_exp':t_exp,'bitdepth':bitdepth,'displaythresh':displaythresh})
        self._previewThread.start()
        

    def getFrame(self,t_exp=None,bitdepth=None):
        t_exp = t_exp or self.t_exp
        bitdepth = bitdepth or self.bitdepth

        # open lib
        ic_ic = IC_ImagingControl()
        ic_ic.init_library()
        
        cam_names = ic_ic.get_unique_device_names()
        cam = ic_ic.get_device(cam_names[0])
        cam.open()
        
        # change camera properties
        cam.gain.auto = False                 # enable auto gain
        cam.gain.value = cam.gain.min
        t_exp_reg = int(np.round(np.log2(t_exp))) # convert exposure time into register value (nearest power of 2)
        
        if t_exp_reg in range(cam.exposure.min,cam.exposure.max+1):
            cam.exposure.value = int(np.round(np.log2(t_exp)))
        else:
            cam.exposure.value = int(cam.exposure.max+cam.exposure.min)/2
            print('Exposure out of range. Setting to half of exposure range')
        
        cam.formats = cam.list_video_formats()
        
        cam.sensor_height = 1080
        cam.sensor_width = 1920
        cam.set_video_format(b'Y800 (1920x1080)')        # use first available video format
        cam.enable_continuous_mode(True)        # image in continuous mode
        cam.start_live(show_display=False)       # start imaging
        
        cam.enable_trigger(True)                # camera will wait for trigger
        if not cam.callback_registered:
            cam.register_frame_ready_callback() # needed to wait for frame ready callback       

        cam.reset_frame_ready()                 # reset frame ready flag

        # send hardware trigger OR call cam.send_trigger() here
        cam.send_trigger()
        # get image data...
        
        cam.wait_til_frame_ready(10)              # wait for frame ready due to trigger
        im = cam.get_image_data()

        img = np.ndarray(buffer=im[0],dtype=np.uint8,shape=(cam.sensor_height,cam.sensor_width,3))
                    
        cam.stop_live()
        cam.close()
        
        ic_ic.close_library()

    def _previewCam(self,t_exp,bitdepth,displaythresh):
        t_exp = t_exp or self.t_exp
        bitdepth = bitdepth or self.bitdepth

        # open lib
        ic_ic = IC_ImagingControl()
        ic_ic.init_library()
        
        cam_names = ic_ic.get_unique_device_names()
        cam = ic_ic.get_device(cam_names[0])
        cam.open()
        
        # change camera properties
        cam.gain.auto = False                 # enable auto gain
        cam.gain.value = cam.gain.min

        t_exp_reg = int(np.round(np.log2(t_exp))) # convert exposure time into register value (nearest power of 2)

        if t_exp_reg in range(cam.exposure.min,cam.exposure.max+1):
            cam.exposure.value = int(np.round(np.log2(t_exp)))
        else:
            cam.exposure.value = int(cam.exposure.max+cam.exposure.min)/2
            print('Exposure out of range. Setting to half of exposure range')
        cam.formats = cam.list_video_formats()
        
        cam.sensor_height = 1080
        cam.sensor_width = 1920
        cam.set_video_format(b'Y800 (1920x1080)')        # use first available video format
        cam.enable_continuous_mode(True)        # image in continuous mode
        cam.start_live(show_display=False)       # start imaging
        
        cam.enable_trigger(True)                # camera will wait for trigger
        if not cam.callback_registered:
            cam.register_frame_ready_callback() # needed to wait for frame ready callback
        
        window_width = 800
        resize_scale = window_width / cam.sensor_width
        rescaled_size = (window_width, int(cam.sensor_height * resize_scale))
        
        cv2.namedWindow('Camera Preview',flags = cv2.WINDOW_KEEPRATIO | cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Preview',rescaled_size[0],rescaled_size[1])
                    
        class MouseControl:
                def __init__(self):
                    self.xy = [0,0]
                    self.im_val = 0
                    self.stopflag = 0
                    self.markers = 0
                    
                def process_events(self,event,x,y,flags,param):
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.stopflag  = not(self.stopflag)
                    elif event == cv2.EVENT_MOUSEMOVE:
                        x_val = int(x)
                        y_val = int(y)
                        self.xy = [x_val,y_val]
                    elif event == cv2.EVENT_RBUTTONDOWN:
                        self.markers = (self.markers + 1) % 3
                        
        #instantiate class
        mouse = MouseControl()
    
        cv2.setMouseCallback('Camera Preview', mouse.process_events)    
            
        while (cv2.getWindowProperty('Camera Preview',0) >= 0):
            try:
                if not(mouse.stopflag):
                    t = time.time()
                    cam.reset_frame_ready()                 # reset frame ready flag
        
                    # send hardware trigger OR call cam.send_trigger() here
                    cam.send_trigger()
                    # get image data...
                    
                    cam.wait_til_frame_ready(10)              # wait for frame ready due to trigger
                    im = cam.get_image_data()

                    img = np.ndarray(buffer=im[0],dtype=np.uint8,shape=(cam.sensor_height,cam.sensor_width,3))
                    
                    cv2.imshow('Camera Preview',img)
                    k = cv2.waitKey(1)
                        
                    if k == 0x1b:
                        cv2.destroyAllWindows()
                        break
                                
                    fps = 1/(time.time()-t)
                else:

                    cv2.imshow('Camera Preview',img)
    
                    k = cv2.waitKey(1)
                        
                    if k == 0x1b:
                        cv2.destroyAllWindows()
                        break
            except:
                print('There was an error')
                cam.stop_live()
                cam.close()
                ic_ic.close_library()
                raise

        cam.stop_live()
        cam.close()
        
        ic_ic.close_library()
