import numpy as np
import cv2
import json
import argparse
import subprocess
import time
import threading
import random

from face_detection import FaceTracker
from face_detection import CaptureManager
from time import sleep

parser = argparse.ArgumentParser(description='Add output pipe')
parser.add_argument('--outpipe1', help='add output pipe 1')
parser.add_argument('--outpipe2', help='add output pipe 2')

args = parser.parse_args()

config = json.load(open("../DeepFusionApp001/dataCoop2/config.json", 'r'))
data_config = config["data"]

temp_name1="temp_coop1.mp4"
temp_name2="temp_coop2.mp4"


# subprocess.call(['rm', '-f', temp_name1])
# subprocess.call(['ffmpeg', '-i', 'coop1.mp4', '-vf', 'scale=800x450',  temp_name1])
# subprocess.call(['rm', '-f', temp_name2])
# subprocess.call(['ffmpeg', '-i', 'coop2.mp4', '-vf', 'scale=800x450',  temp_name2])
# # subprocess.call(['ffmpeg', '-i', 'coop1.mp4', '-filter:v', 'setpts=0.1*PTS', '-vf', 'scale=480X270',  'coop.mp4'])

# capture = data_config["capture"]
capture1 = temp_name1
print capture1
video_capture1 = cv2.VideoCapture(capture1)

while not video_capture1.isOpened():
    video_capture1 = cv2.VideoCapture(capture1)
    cv2.waitKey(1000)
    print "Wait for the header 1"

capture2 = temp_name2
print capture2
video_capture2 = cv2.VideoCapture(capture2)

while not video_capture1.isOpened():
    video_capture2 = cv2.VideoCapture(capture2)
    cv2.waitKey(1000)
    print "Wait for the header 2"



def video1():
    start_time1=time.time()
    num1=0
    while video_capture1.isOpened():
        num1+=1

        capture_manager = CaptureManager(video_capture1, True)
        face_tracker = FaceTracker()
        capture_manager.enter_frame()

        if num1 % 2 == 0:
        # if False:
            pass
        else:
            frame1 = capture_manager.frame

            face_tracker.update(frame1)
            face_tracker.draw_debug_rects(frame1)
            capture_manager.exit_frame()
            ret, jpeg1 = cv2.imencode(".jpg", frame1)

            f1 = open(args.outpipe1, 'wb', 0)
            f1.write(jpeg1)
            f1.close()
            # sleep(0.001)

            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

        if num1%20==0:
            print num1/(time.time()-start_time1)

    # When everything done, release the capture
    video_capture1.release()
    cv2.destroyAllWindows()

def video2():
    start_time2=time.time()
    num2=0
    while video_capture2.isOpened():
        num2+=1

        capture_manager = CaptureManager(video_capture2, True)
        face_tracker = FaceTracker()
        capture_manager.enter_frame()

        if num2 % 2 == 0:
        # if False:
            pass
        else:
            frame2 = capture_manager.frame

            face_tracker.update(frame2)
            face_tracker.draw_debug_rects(frame2)
            capture_manager.exit_frame()
            ret, jpeg2 = cv2.imencode(".jpg", frame2)

            f2 = open(args.outpipe2, 'wb', 0)
            f2.write(jpeg2)
            f2.close()
            # sleep(0.001)

            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

        if num2%20==0:
            print num2/(time.time()-start_time2)

    # When everything done, release the capture
    video_capture1.release()
    cv2.destroyAllWindows()


def mockup():
    graphite_ipaddress = config["runtime"]["graphite_ipaddress"]
    path_1 = "feng.coop1.mockup1"
    path_2 = "feng.coop1.mockup2"
    path_3 = "feng.coop1.mockup3"
    path_4 = "feng.coop2.mockup1"
    path_5 = "feng.coop2.mockup2"
    path_6 = "feng.coop2.mockup3"
    mock_num = 0
    while mock_num < 100:
        mock_num += 1
        try:
            subprocess.check_output(["echo \"" + path_1 + " " + str(random.randint(1,100)) +
                                     " `date +%s`\" | nc " + "10.40.170.137" + " 2003"], shell=True)
            subprocess.check_output(["echo \"" + path_2 + " " + str(random.randint(1,100)) +
                                     " `date +%s`\" | nc " + "10.40.170.137" + " 2003"], shell=True)
            subprocess.check_output(["echo \"" + path_3 + " " + str(random.randint(1,100)) +
                                     " `date +%s`\" | nc " + "10.40.170.137" + " 2003"], shell=True)
            subprocess.check_output(["echo \"" + path_4 + " " + str(random.randint(1, 100)) +
                                     " `date +%s`\" | nc " + "10.40.170.137" + " 2003"], shell=True)
            subprocess.check_output(["echo \"" + path_5 + " " + str(random.randint(1, 100)) +
                                     " `date +%s`\" | nc " + "10.40.170.137" + " 2003"], shell=True)
            subprocess.check_output(["echo \"" + path_6 + " " + str(random.randint(1, 100)) +
                                     " `date +%s`\" | nc " + "10.40.170.137" + " 2003"], shell=True)
        except:
            print "write data to graphite (" + graphite_ipaddress + ") failed"

        time.sleep(1)


t1 = threading.Thread(target=video1)
t2 = threading.Thread(target=video2)
t3 = threading.Thread(target=mockup)
t1.start()
t2.start()
t3.start()
