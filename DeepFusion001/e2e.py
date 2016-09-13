#!/usr/bin/python
import os
import subprocess
from glob import glob
import numpy as np
import cv2
import json
import itertools
import matplotlib.pyplot as plt
from drawnow import drawnow
import time
from sympy import Point, Polygon

import track_v04 as tracker

from scipy.misc import imread
#from IPython import display
import apollocaffe # Make sure that caffe is on the python path:

from utils.annolist import AnnotationLib as al
from train import load_idl_list, forward
from utils import load_data_mean, Rect, stitch_rects

def testScope():
    print "testScope peopleCount:%s" % peopleCount

os.system("rm tmp/*.jpg")
os.system("rm tmp/*.mp4")

parser = apollocaffe.base_parser()
parser.add_argument('--config', required=True)
args = parser.parse_args()

config = json.load(open(args.config, 'r'))

apollocaffe.set_random_seed(config["solver"]["random_seed"])
apollocaffe.set_device(3)  

data_mean = load_data_mean(config["data"]["idl_mean"], 
                           config["net"]["img_width"], 
                           config["net"]["img_height"], image_scaling=1.0)

config["data"]["test_idl"] = config["data"]["test_idl_foreval"] 
runtimedir = "./data_input/cam1/"
runtimedir_init = "./data_input/nortechInit/"

roi_x_left = config["runtime"]["roi_x_left"];
roi_x_right = config["runtime"]["roi_x_right"];
roi_y_top = config["runtime"]["roi_y_top"];
roi_y_bottom = config["runtime"]["roi_y_bottom"];

ROI_threshold = [
    config["runtime"]["roi_x_left"],
    config["runtime"]["roi_x_right"],
    config["runtime"]["roi_y_top"],
    config["runtime"]["roi_y_bottom"]] 

ROI = Polygon((roi_x_left,roi_y_top),(roi_x_right,roi_y_top),
    (roi_x_right,roi_y_bottom), (roi_x_left, roi_y_bottom))

doTracking = tracker.Orchestrator()

num_init_images = 6
test_list = list(itertools.islice(
        load_idl_list(runtimedir_init + "all.idl", data_mean, config["net"], False, False),
        0,
        num_init_images))

net = apollocaffe.ApolloNet()
net.phase = 'test'
forward(net, test_list[0], config["net"], True)
net.load(config["data"]["weights"])

net_config = config["net"]
pix_per_w = net_config["img_width"]/net_config["grid_width"]
pix_per_h = net_config["img_height"]/net_config["grid_height"]
min_confidence = config["runtime"]["min_confidence"]

try:
#    ret = subprocess.check_output(["cd %s && rm *.png" % runtimedir],shell=True)
    ret = 1
except:
    print "nothing to clean"
lastcount = 0

def processImagesInDirectory(runtimedir, autodelete, printmode):
    frames = sorted(glob(runtimedir + '*.png'))
    num_test_images = len(frames) 
    if(num_test_images == 0):
        time.sleep(.05)
    else:
        ret = subprocess.check_output(["cd %s && ../../yamltoidl.pl runtime" % runtimedir],shell=True)
        test_list = list(itertools.islice(
                load_idl_list(runtimedir + "all.idl", data_mean, config["net"], False, False),
                0,
                num_test_images))

        annolist = al.AnnoList()
        for i in range(len(frames)):
            peopleCount = 0
            t0=time.clock()     
            inputs = test_list[i]
            # temporary below used by displayTrackingResukts
            frameName = inputs["imname"]
            step = i
            delay = 0
            # temporary above
            if printmode:
                print i, inputs["imname"]

            bbox_list, conf_list = forward(net, inputs, net_config, True)
            
            img = np.copy(inputs["raw"])
            png = np.copy(inputs["imname"])
            all_rects = [[[] for x in range(net_config["grid_width"])] for y in range(net_config["grid_height"])]
            for n in range(len(bbox_list)):
                for k in range(net_config["grid_height"] * net_config["grid_width"]):
                    y = int(k / net_config["grid_width"])
                    x = int(k % net_config["grid_width"])
                    bbox = bbox_list[n][k]
                    conf = conf_list[n][k,1].flatten()[0]
                    abs_cx = pix_per_w/2 + pix_per_w*x + int(bbox[0,0,0])
                    abs_cy = pix_per_h/2 + pix_per_h*y+int(bbox[1,0,0])
                    w = bbox[2,0,0]
                    h = bbox[3,0,0]
                    all_rects[y][x].append(Rect(abs_cx,abs_cy,w,h,conf))

            acc_rects = stitch_rects(all_rects, net_config)
           
            GatherBB = np.array([[] for z in range(4)]).T

            display = True 
            if display:
                for rect in acc_rects:
                    if rect.true_confidence < min_confidence:
                        #print rect.true_confidence
                        continue
                    cv2.rectangle(img, 
                                  (rect.cx-int(rect.width/2), rect.cy-int(rect.height/2)), 
                                  (rect.cx+int(rect.width/2), rect.cy+int(rect.height/2)), 
                                  (255,0,0),
                                  2)  #BGR
            	    peopleCount = peopleCount + 1; 

                    BB = np.array([[rect.cx-int(rect.width/2),rect.cy-int(rect.height/2),int(rect.width),int(rect.height)]])            
                    GatherBB=np.concatenate((GatherBB,BB), axis=0)
                #plt.figure(figsize=(15,10))
                
            
                img = img[:, :, (2, 1, 0)]  #convert to RGB
                t1=time.clock()
                #print t1-t0
                #cv2.imshow('image',img)
                cv2.imwrite("./tmp/zot_%05d.jpg" % i, img)
                cv2.waitKey(100)        #[ms]

# counting
            if printmode:
                print "count: %d" % peopleCount
            path_rawcount = config["runtime"]["path_rawcount"] 
            graphite_ipaddress = config["runtime"]["graphite_ipaddress"]
            if printmode:
                try:
                    ret = subprocess.check_output(["echo \"" + path_rawcount + " " +
                        str(peopleCount) + " `date +%s`\" | nc " + graphite_ipaddress +  " 2003"],
                        shell=True)
                except:
                    print "write data to graphite (" + graphite_ipaddress + ") failed" 

# tracking
            doTracking.loadBB(np.matrix(GatherBB))
            doTracking.predictNewLocationsOfTracks()  
            matches, unmatchedTracks, unmatchedDetections = doTracking.detectionToTrackAssignment() 
            doTracking.updateAssignedTracks(matches)
            doTracking.updateUnassignedTracks( unmatchedTracks)
            doTracking.deleteLostTracks( ROI_threshold )
            doTracking.createNewTracks(unmatchedDetections)
            doTracking.displayTrackingResukts(frameName, step, delay, img)

        #os.system("./doMpegHml.sh " + config["runtime"]["outmp4_filename"])
        if autodelete:
            ret = subprocess.check_output(["cd %s && rm *.png" % runtimedir],shell=True)

processImagesInDirectory(runtimedir_init,False,False)

while(True): 
    processImagesInDirectory(runtimedir,True,True)

