#!/usr/bin/python
import os
import subprocess
import numpy as np
import cv2
import json
import itertools
import matplotlib.pyplot as plt
from drawnow import drawnow
 
from scipy.misc import imread
 
import apollocaffe # Make sure that caffe is on the python path:

from utils.annolist import AnnotationLib as al
from train import load_idl_list, forward
from utils import load_data_mean, Rect, stitch_rects

parser = apollocaffe.base_parser()
parser.add_argument('--config', required=True)
args = parser.parse_args()

config = json.load(open(args.config, 'r'))

data_mean = load_data_mean(config["data"]["idl_mean"], 
                           config["net"]["img_width"], 
                           config["net"]["img_height"], image_scaling=1.0)

num_test_images = 500 
idlfile = config["data"]["test_idl"]
idlfile = "workdir/gt/all.idl"
annolist = al.parse(idlfile)
subprocess.check_output(["rm -fr workdir/gt/gtImages"],shell=True)
subprocess.check_output(["mkdir -p workdir/gt/gtImages"],shell=True)

for i in range(num_test_images):    
    a = annolist[i]
    imageName = os.path.join(
        os.path.dirname(os.path.realpath(idlfile)),a.imageName)
    print i, imageName
    img = imread(imageName)

    for j in range(len(a.rects)):
        print a.rects[j].x1,a.rects[j].y1,a.rects[j].x2,a.rects[j].y2
        cv2.rectangle(img,
            (int(a.rects[j].x1),int(a.rects[j].y1)),
            (int(a.rects[j].x2),int(a.rects[j].y2)),
            (255,0,0),
            2)
    filename = "workdir/gt/gtImages/gtImage%04d.png" % i;
    cv2.imwrite(filename,img);
#    cv2.imshow('image',img)
#    cv2.waitKey(30000)
