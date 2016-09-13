"""
python AUO_loc_02.py --config configSmartCities.json --cam 2 --gpu 2

"""
import numpy as np
import cv2
import json
import itertools
import time

from scipy.misc import imread
 
import apollocaffe # Make sure that caffe is on the python path:

from utils.annolist import AnnotationLib as al
from trainMall import load_idl_list, forward
from utils import load_data_mean, Rect, stitch_rects



def doLocalization(config, cam, gen, tag):

    net_config  = config["net"]
    data_config = config["data"]
    solver      = config["solver"]
    
    apollocaffe.set_random_seed(solver["random_seed"])
    #apollocaffe.set_device(solver["gpu"])   

    data_idl_mean = data_config["cam" + cam]["idl_mean"]
    data_test_poc = data_config["cam" + cam]["test_poc"]
    data_test_model = data_config["cam" + cam]["test_model"]
    num_test_images =data_config["cam" + cam]["num_test_images"]
    frame_from=data_config["cam" + cam]["frame_min"]
    frame_to=data_config["cam" + cam]["frame_max"]
       
    print "Configuration: ", data_idl_mean,data_test_poc,data_test_model
    fileModel = ('./all_%s_%02d.idl') % (tag,int(gen))
    print "Model saved on: %s" % fileModel

    data_mean = load_data_mean(data_idl_mean, 
                           config["net"]["img_width"], 
                           config["net"]["img_height"], image_scaling=1.0)

    isFarField = data_config["fieldView"]
    print "isFarField: ", isFarField

 
    print 'frame_from=%d frame_to=%d num_test_images=%d' % (frame_from, frame_to, num_test_images)

    # Warning: load_idl returns an infinite generator. Calling list() before islice() will hang.
    test_list = list(itertools.islice(
        load_idl_list( data_test_poc, data_mean, config["net"], False, False),
        0,
        num_test_images))

    net = apollocaffe.ApolloNet()
    net.phase = 'test'
    forward(net, test_list[0], config["net"], True)
    net.load(data_test_model )

    annolist = al.AnnoList()
    net_config = config["net"]
    pix_per_w = net_config["img_width"]/net_config["grid_width"]
    pix_per_h = net_config["img_height"]/net_config["grid_height"]


    display = True

    for step in range(frame_from,frame_to):
        countBB = 0
#
# .. doDecoding using learned MALL model
#    
        inputs = test_list[step]
    

        bbox_list, conf_list = forward(net, inputs, net_config, True)
    
        img = np.copy(inputs["raw"])
        overlay = img.copy()
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
       
        GatherBB=np.array([[] for z in range(4)]).T
     
        if display:
            for rect in acc_rects:
                #if (rect.true_confidence < 0.85) | (rect.cy < 150) | (rect.cx < 300):
                if (rect.true_confidence < 0.85) :                
                    #print rect.true_confidence
                    continue
                else:
                    countBB += 1
        #
        # ... gather BB(s) for the active frame with confidence level at least of 80%                
        #        
                BB = np.array([[rect.cx-int(rect.width/2),rect.cy-int(rect.height/2),int(rect.width),int(rect.height)]])            
                GatherBB=np.concatenate((GatherBB,BB), axis=0)
                                               
            #---> remove (+)
                if isFarField == True:
                    X = rect.cx-int(rect.width/2)
                    Y = rect.cy-int(rect.height/2)
                    #R = 20
                    #cv2.circle(overlay, (X,Y), R, (235,235,0), -1)  
                    cv2.rectangle(overlay,(X,Y),(X+40,Y+40),(255,255,0),-2)
                else:
                    cv2.rectangle(img, 
                          (rect.cx-int(rect.width/2), rect.cy-int(rect.height/2)), 
                          (rect.cx+int(rect.width/2), rect.cy+int(rect.height/2)), 
                          (255,0,0),
                          2)  #BGR
                    #cv2.putText(img,"%3.2f"%rect.true_confidence, (rect.cx-int(rect.width/2), rect.cy-int(rect.height/2)),
                    #        cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.8, (255,255,0), 1)
                        
            if isFarField == True:
                opacity = 0.6
                cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)                
            img = img[:, :, (2, 1, 0)]  #convert to RGB
        

            cv2.imshow('image',img)
        
            cv2.imwrite("./tmp/CLB_cam2_2fps_%05d.png" % (step-frame_from), img);
            cv2.waitKey(1300)        #[ms]
            
            
        #----->  ONLY FOR TRAINING
        #print step, np.shape(GatherBB)
    
        #print step, inputs["imname"],  countBB
        print (step-frame_from + 1), countBB
         
        doPrint = True
        if doPrint:
            anno = al.Annotation()
            anno.imageName = inputs["imname"]
            for rect in acc_rects:
                r = al.AnnoRect()
                r.x1 = rect.cx - rect.width/2.
                r.x2 = rect.cx + rect.width/2.
                r.y1 = rect.cy - rect.height/2.
                r.y2 = rect.cy + rect.height/2.
                #r.score = rect.true_confidence
                if rect.true_confidence>0.85: anno.rects.append(r)
            annolist.append(anno)
            annolist.save( fileModel )
#
# .............................................................................            
#
def main():

    parser = apollocaffe.base_parser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--cam', required=True)
    parser.add_argument('--gen', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    print "args.config: ", args.config
    print "args.cam: ", args.cam   
    print "args.gen: ", args.gen
    print "args.tag: ", args.tag 
    config = json.load(open(args.config, 'r'))

    print "args.gpu: ", args.gpu
    apollocaffe.set_device(args.gpu)
    
    doLocalization(config, args.cam, args.gen, args.tag)

if __name__ == "__main__":
    main()
       


