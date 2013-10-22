#!/usr/bin/python
#
# Camera control specialized for a Hamamatsu camera.
#
# Hazen 10/13
#

from PyQt4 import QtCore
import os
import platform
import traceback

# Debugging
import halLib.hdebug as hdebug

import camera.frame as frame
import camera.cameraControl as cameraControl
import hamamatsu.hamamatsu_camera as hcam

class ACameraControl(cameraControl.CameraControl):
    @hdebug.debug
    def __init__(self, parameters, parent = None):
        cameraControl.CameraControl.__init__(self, parameters, parent)

        self.stop_at_max = True

        if hasattr(parameters, "camera_id"):
            self.camera = hcam.HamamatsuCameraMR(parameters.camera_id)
        else:
            self.camera = hcam.HamamatsuCameraMR(0)

    @hdebug.debug
    def closeShutter(self):
        self.shutter = False
        self.stopCamera()

    @hdebug.debug
    def getAcquisitionTimings(self):
        frame_rate = self.camera.getPropertyValue("internal_frame_rate")[0]
        temp = 1.0/frame_rate
        return [temp, temp, temp]

    @hdebug.debug
    def getTemperature(self):
        return ["na", "stable"]

    @hdebug.debug
    def newFilmSettings(self, parameters, filming = False):
        self.stopCamera()
        self.parameters = parameters
        p = parameters
        if filming:
            if (p.acq_mode == "fixed_length"):
                self.stop_at_max = True
            else:
                self.stop_at_max = False
        self.filming = filming

    @hdebug.debug
    def newParameters(self, parameters):
        p = parameters
        self.newFilmSettings(parameters)

        try:
            # Set ROI location and size.
            self.camera.setPropertyValue("subarray_hpos", p.x_start)
            self.camera.setPropertyValue("subarray_hsize", p.x_pixels)
            self.camera.setPropertyValue("subarray_vpos", p.y_start)
            self.camera.setPropertyValue("subarray_vsize", p.y_pixels)

            # Set binning.
            if (p.x_bin != p.y_bin):
                raise AssertionError("unequal binning is not supported.")
            if (p.x_bin == 1):
                self.camera.setPropertyValue("binning", "1x1")
            elif (p.x_bin == 2):
                self.camera.setPropertyValue("binning", "2x2")
            elif (p.x_bin == 4):
                self.camera.setPropertyValue("binning", "4x4")
            else:
                raise AssertionError("unsupported bin size", p.x_bin)

            # Set the rest of the hamamatsu properties.
            #
            # Note: These could overwrite the above. For example, if you
            #   have both "x_start" and "subarray_hpos" in the parameters
            #   file then "subarray_hpos" will overwrite "x_start". Trouble
            #   may follow if they are not set to the same value.
            #
            for key, value in p.__dict__.iteritems():
                if (key == "binning"): # sigh..
                    continue
                if self.camera.isCameraProperty(key):
                    self.camera.setPropertyValue(key, value)

            self.got_camera = True

        except:
            print "QCameraThread: Bad camera settings"
            print traceback.format_exc()
            self.got_camera = False

    @hdebug.debug
    def openShutter(self):
        self.shutter = True
        self.stopCamera()

    @hdebug.debug
    def quit(self):
        self.stopThread()
        self.wait()
        self.camera.shutdown()

    def run(self):
        while(self.running):
            self.mutex.lock()
            if self.acquire.amActive() and self.got_camera:

                # Get data from camera and create frame objects.
                [frames, frame_size] = self.camera.getFrames()

                # Check if we got new frame data.
                if (len(frames) > 0):

                    # Create frame objects.
                    frame_data = []
                    for hc_data in frames:
                        aframe = frame.Frame(hc_data.getData(),
                                             self.frame_number,
                                             frame_size[0],
                                             frame_size[1],
                                             "camera1",
                                             True)
                        frame_data.append(aframe)

                        self.frame_number += 1
                        if self.filming and self.stop_at_max and (self.frame_number == self.parameters.frames):
                            self.max_frames_sig.emit()
                            break

                    # Save frames if we are filming.
                    if self.filming and self.daxfile:
                        for aframe in frame_data:
                            self.daxfile.saveFrame(aframe)

                    # Emit new data signal
                    self.newData.emit(frame_data, self.key)

            else:
                self.acquire.idle()

            self.mutex.unlock()
            self.msleep(5)

    @hdebug.debug        
    def startCamera(self, key):
        self.mutex.lock()
        self.acquire.go()
        self.key = key
        self.frame_number = 0
        self.max_frames_sig.reset()
        if self.got_camera:
            self.camera.startAcquisition()
        self.mutex.unlock()

    @hdebug.debug
    def stopCamera(self):
        if self.acquire.amActive():
            self.mutex.lock()
            if self.got_camera:
                self.camera.stopAcquisition()
            self.acquire.stop()
            self.mutex.unlock()
            while not self.acquire.amIdle():
                self.usleep(50)

#
# The MIT License
#
# Copyright (c) 2013 Zhuang Lab, Harvard University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
