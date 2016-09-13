import numpy as np
import cv2
import time

from face_detection import FaceTracker
from face_detection import CaptureManager

# cap=cv2.VideoCapture("C:/Users/fengjia/Desktop/try/coop3.mpg")
cap=cv2.VideoCapture("./coop1.mp4")
#cap = cv2.VideoCapture(0)

# face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
# eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')


while not cap.isOpened():
    cap = cv2.VideoCapture("./coop1.mp4")
    cv2.waitKey(1000)
    print "Wait for the header"

# while(True):
while (cap.isOpened()):
    print 1

    # ret, frame = cap.read()

    # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # ret, jpeg = cv2.imencode(".jpg", gray)
    # f = open("./temp.jpg", 'wb', 0)
    # f.write(jpeg)
    # f.close()
	
	

	###########################
    # ret, frame = cap.read()

    # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    # for (x, y, w, h) in faces:
        # cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        # roi_gray = gray[y:y + h, x:x + w]
        # roi_color = frame[y:y + h, x:x + w]
        # eyes = eye_cascade.detectMultiScale(roi_gray)
        # for (ex, ey, ew, eh) in eyes:
            # cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)
			
    
	
	
	#############################
	
    capture_manager = CaptureManager(cap, True)
    face_tracker = FaceTracker()

    capture_manager.enter_frame()
    frame = capture_manager.frame
    face_tracker.update(frame)
    face_tracker.draw_debug_rects(frame)
    capture_manager.exit_frame()
	
	
	
	
	
	
	################cv2.imshow('img', frame)
    ret, jpeg = cv2.imencode(".jpg", frame)
    f = open("./temp.jpg", 'wb', 0)
    f.write(jpeg)
    f.close()
	
    # time.sleep(0.1)
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
