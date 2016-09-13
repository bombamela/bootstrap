# This version use flask for streaming video
#
# python e2e_062.py --config configclean.json --cam 2 --gpu 2
#

import numpy as np
import cv2
import json
import itertools
 
import track_v06 as tracker
import time
import apollocaffe  
from utils.annolist import AnnotationLib as al
from train_01  import load_idl_list, read_frame, forward
from utils import load_data_mean, Rect, stitch_rects

from flask import Flask, render_template, Response
 
# ------------------------ Configuration set-up -------------------------------
 
parser = apollocaffe.base_parser()
parser.add_argument('--config', required=True)
parser.add_argument('--cam', required=True)
args = parser.parse_args()
cam = args.cam
print "args.config: ", args.config
print "args.cam ", cam    
config = json.load(open(args.config, 'r'))

gpu =  args.gpu
#apollocaffe.set_device(args.gpu)

net_config  = config["net"]
data_config = config["data"]

#solver      = config["solver"]  
#apollocaffe.set_random_seed(solver["random_seed"])
#apollocaffe.set_device(solver["gpu"])  

data_idl_mean   = data_config["cam" + cam]["idl_mean"]
data_test_poc   = data_config["cam" + cam]["test_poc"]
data_test_model = data_config["cam" + cam]["test_model"]
num_test_images = data_config["cam" + cam]["num_test_images"]
frame_from      = data_config["cam" + cam]["frame_min"]
frame_to        = data_config["cam" + cam]["frame_max"]
capture         = data_config["capture_mjpg"]
#capture         = data_config["capture_rtsp"]
                            
print  data_idl_mean,data_test_poc, data_test_model, capture
print 'frame_from=%d frame_to=%d num_test_images=%d' % (frame_from, frame_to, num_test_images)
 
print ">>> END of CONFIG"
# --------------------------------------------------------
app = Flask(__name__)
 

@app.route('/')
def index():
    return render_template('index.html')

def gen(doTrack):
    print ">>> INSIDE gen(dotrack)"
    frameCounter = -1
        
    print "args.gpu: ", gpu
    apollocaffe.set_device(gpu)
    net_config = config["net"]
    
    data_mean = load_data_mean(data_idl_mean, 
                           net_config["img_width"], 
                           net_config["img_height"], image_scaling=1.0)
    
    video_capture = cv2.VideoCapture( capture )
    video_capture, test_list = read_frame(video_capture, data_mean, capture)
    
    #num_test_images = data_config["num_test_images"]  
    print "num_test_images: ", num_test_images

    # Warning: load_idl returns an infinite generator. Calling list() before islice() will hang.
    #test_list = list(itertools.islice(load_idl_list(data_test_poc, data_mean, config["net"], False, False),0,num_test_images))
    
    
    net = apollocaffe.ApolloNet()
    net.phase = 'test'
    forward(net, test_list, net_config, True)  #test_list[0]
    net.load(data_test_model)

    annolist = al.AnnoList()
    
    pix_per_w = net_config["img_width"]/net_config["grid_width"]
    pix_per_h = net_config["img_height"]/net_config["grid_height"]

    display = True
    delay= config["logging"]["display_delay_ms"]
    #frame_min=config["logging"]["frame_min"]
    #frame_max=config["logging"]["frame_max"]
    ROI_Threshold = data_config["ROI_Threshold"]    #[X_left, X_right, Y_top, Y_bottom]
 
     
    CIC_Threshold = data_config["CIC_Threshold"]
    Verbose = data_config["Verbose"]
    #Outfile = config["logging"]["Outfile"]
    costUnassignedTracks = data_config["costUnassignedTracks"]
    print "costUnassignedTracks: ", costUnassignedTracks
    
    while True:
        frameCounter = frameCounter + 1
        step = frameCounter % (frame_to - frame_from) + frame_from
        print step,frameCounter,frame_to,frame_from
        
        
        video_capture, inputs = read_frame(video_capture, data_mean, capture, step)
        #inputs = test_list[step]
        frameName = inputs["imname"]
        print frameName 
         
        t0=time.clock() 
        bbox_list, conf_list = forward(net, inputs, net_config, True)
    
        grid_height = net_config["grid_height"]
        grid_width  = net_config["grid_width"]
        
        img = np.copy(inputs["raw"])
        png = np.copy(inputs["imname"])
        all_rects = [[[] for x in range(grid_width )] for y in range( grid_height) ]        
        
        for n in range(len(bbox_list)):
            for k in range(grid_height * grid_width):
                y = int(k / grid_width)
                x = int(k % grid_width)
                bbox = bbox_list[n][k]
                conf = conf_list[n][k,1].flatten()[0]
                abs_cx = pix_per_w/2 + pix_per_w*x + int(bbox[0,0,0])
                abs_cy = pix_per_h/2 + pix_per_h*y+int(bbox[1,0,0])
                w = bbox[2,0,0]
                h = bbox[3,0,0]
                all_rects[y][x].append(Rect(abs_cx,abs_cy,w,h,conf))

        acc_rects = stitch_rects(all_rects, net_config)
       
        GatherBB=np.array([[] for z in range(4)]).T
        t1=time.clock() 
        if display:
            for rect in acc_rects:
                Y_t = ROI_Threshold[2]
                X_l = ROI_Threshold[0]
                if (rect.true_confidence < 0.80 ):
                    #print rect.true_confidence
                    continue
 
                BB = np.array([[rect.cx-int(rect.width/2),rect.cy-int(rect.height/2),int(rect.width),int(rect.height)]])            
                GatherBB=np.concatenate((GatherBB,BB), axis=0) 
                                                             
 #
 # .. do Tracking with GatherBB as input
 #
        print step, inputs["imname"],  np.shape(GatherBB)

        doTrack.loadBB(np.matrix(GatherBB))   
        doTrack.predictNewLocationsOfTracks()           
        Regular, LostTracks, NewDetections = doTrack.detectionToTrackAssignment(costUnassignedTracks)      
        doTrack.updateAssignedTracks(Regular)
        doTrack.updateUnassignedTracks( LostTracks)
        doTrack.deleteLostTracks( ROI_Threshold , CIC_Threshold, step)
        doTrack.createNewTracks( NewDetections, step)
        t2=time.clock()

        frame = doTrack.displayTrackingResults(frameName, step, img, delay )
        t3=time.clock()
        print 'TIMING: All:%f D:%f T:%f L:%f\n' % (t3-t0,t3-t2,t2-t1,t1-t0)      
        #time.sleep(0.200)

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    print ">>> VIDEO_FEED"
    return Response( gen( tracker.Orchestrator() ), mimetype='multipart/x-mixed-replace; boundary=frame')

# .............................................................................            


if __name__ == "__main__":
    print ">>> MAIN "
    app.run(host='0.0.0.0', debug=True, threaded=True)

