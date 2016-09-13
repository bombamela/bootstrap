#  track_v01.py
#  
#  Copyright 2015 elf <hduser@JASMINE>
# 
#  
#  
# 31.10.2015 
#
import numpy as np
import cv2
import KalmanFilterObj as KFO
import GetMallDetection as Mall

#
# ... Track structure definition
#
class Track(object):
    def __init__(self, id_=-1, bbox=[], hKF=0, age=1, totalVisibleCount=1, consecutiveInvisibleCount=0):
        self.id = id_
        self.bbox = np.matrix(bbox)
        self.kalmanFilter = hKF
        self.age = age
        self.totalVisibleCount = totalVisibleCount
        self.consecutiveInvisibleCount = consecutiveInvisibleCount
    def __getitem__(self, key):
        return self.__dict__[key]
    def __setitem__(self, key, value):
        self.__dict__[key] = value
#  
#  name: Orchestrator
#  @param
#  @return
#
# ... Tracking orchestration given bb(s) from LSTM decoder
#
class Orchestrator( object):
    def __init__(self):
        self.__Tracks = []
        self.__Centroids = []
        self.__BBoxes = []
        self.__nextTrackId=1
   
  
    def loadBB(self, BBoxes):
        # BBox = [Xo, Yo, W, H]
        self.__BBoxes = BBoxes
        self.__Centroids = BBoxes[:, 0:2] + BBoxes[:, 2:4]/2   
        #print self.__BBoxes
        #print self.__Centroids
          
    def predictNewLocationsOfTracks(self):
        nTracks = len(self.__Tracks)
        #print "++ predictNewLocations: %d" % nTracks
        
        
        for n in range(nTracks):
            bbox = self.__Tracks[n].__getitem__('bbox')
            hKF = self.__Tracks[n].__getitem__('kalmanFilter')
            hKF.kf_predict()
            #print "Predict: ", n, hKF.X
            #print type(bbox), np.shape(bbox)
             
            predictedCentroid = hKF.X[0:2].T - bbox[:, 2:4]/2 
            newbbox = np.matrix(np.hstack((predictedCentroid, bbox[:, 2:4])))
            #print 'newbox: ', newbbox
            self.__Tracks[n].__setitem__('bbox', newbbox)
     
         
    def detectionToTrackAssignment(self, costUnassignedTracks = 50):        
        nTracks = len(self.__Tracks)
        #print "++ detectionToTrackAssignment: %d" % nTracks
        
        nDetections = self.__Centroids.shape[0] 
        #print "nTracks %d nDetection: %d" % (nTracks, nDetections)
        cost = np.matrix( np.zeros((nTracks, nDetections)))
        for n in range( nTracks):
            hKF = self.__Tracks[n].__getitem__('kalmanFilter')
            cost[n, :] = hKF.kf_distance( self.__Centroids.T )
             
        matches, unmatchedTracks, unmatchedDetections = KFO.assignDetectionsToTracks(cost, costUnassignedTracks)
        #print type(matches)
        return matches, unmatchedTracks, unmatchedDetections
          
        
    def updateAssignedTracks(self, matches):
        #print matches
  
        nAssignedTracks = len(matches)
        #print "++ updateAssignedTracks: %d" % nAssignedTracks
        
        for n in range(nAssignedTracks):
            trackId = matches[n, 0]
            detectionId = matches[n, 1]
            centroid = self.__Centroids[detectionId, :]
            bbox = self.__BBoxes[detectionId, :]
            
            hKF = self.__Tracks[trackId].__getitem__('kalmanFilter')
            hKF.kf_update( centroid.T )
            
            self.__Tracks[trackId].__setitem__('bbox', bbox)
            
            age = self.__Tracks[trackId].__getitem__('age')
            self.__Tracks[trackId].__setitem__('age', age+1)
        
            totalVisibleCount = self.__Tracks[trackId].__getitem__('totalVisibleCount')
            self.__Tracks[trackId].__setitem__('totalVisibleCount', totalVisibleCount+1)
        
            self.__Tracks[trackId].__setitem__('consecutiveInvisibleCount', 0 )
            
             
    def updateUnassignedTracks(self, unmatchedTracks):
        nUnmatchedTracks = len(unmatchedTracks)
        #print "++ updateUnassignedTracks %d" % nUnmatchedTracks
        
        for n in range(nUnmatchedTracks):
            trackId = unmatchedTracks[n]
            
            age = self.__Tracks[trackId].__getitem__('age')
            self.__Tracks[trackId].__setitem__('age', age+1)
            
            consecutiveInvisibleCount = self.__Tracks[trackId].__getitem__('consecutiveInvisibleCount')
            self.__Tracks[trackId].__setitem__('consecutiveInvisibleCount', consecutiveInvisibleCount+1)

 
    def deleteLostTracks(self, ROI_thresholds):
        # ROI_thresholds = [X_l, X_r, Y_t, Y_b]
        
        #print "++ deleteTracks ++"
        if self.__Tracks:
            delindex = []
            nTracks = len(self.__Tracks)
            for n in range( nTracks ):
                hKF = self.__Tracks[n].__getitem__('kalmanFilter') 
                Yu = hKF.X[1]  #value computed after kf_update()
                Xu = hKF.X[0];
                Vxu = hKF.X[2]
                Vyu = hKF.X[3]
                if ((Yu < ROI_thresholds[2] ) & (Vyu < 0.0)) | \
                    ((Xu < ROI_thresholds[0] ) & (Vxu < 0.0)) | \
                    ((Yu > ROI_thresholds[3] ) & (Vyu > 0.0)):
                    delindex.append(n)
                 
                    #print "Track #%d will be removed\n" % self.__Tracks[n].id
                    
            if delindex:
                #print delindex
                for o,d in enumerate(delindex):
                    d -= o
                    del self.__Tracks[d]
                    
                
                
        
        
    def createNewTracks(self, unmatchedDetections):
        nTracks = len(self.__Tracks)    
        #print "++ createNewTracks %d" % nTracks
        #print unmatchedDetections
        
        for n in unmatchedDetections:
            centroid = self.__Centroids[n, :]
            bbox = self.__BBoxes[n, :]
            
            Vo = np.array([[0, 0]])
            #print centroid, Vo
            initialGuess = np.hstack((centroid, Vo))
            #print "Initial Guess: ", initialGuess
            kalmanFilter = KFO.KalmanFilterObj(initialGuess, [100, 100], [0, 0, 100, 50], [100, 100, 100, 100], 1)
            newTrack = Track(self.__nextTrackId, bbox, kalmanFilter)
            
            self.__Tracks.append(newTrack)
            self.__nextTrackId += 1
      
      
              
    def displayTrackingResukts(self, frameName, step, delay=1000, img=np.array([])):
        
        #print "processing filename: %s" % frameName
    
        readFromFile=False
        if np.size(img)==0:
            readFromFile=True
            
        minVisibleCount=1
        
        if self.__Tracks:   
            nTracks = len(self.__Tracks)
            cond_TVC=np.array([self.__Tracks[n].__getitem__('totalVisibleCount') for n in range(nTracks)])
            cond_CIC=np.array([self.__Tracks[n].__getitem__('consecutiveInvisibleCount') for n in range(nTracks)])
            reliableTracks = np.where(np.logical_and(cond_TVC>minVisibleCount, cond_CIC==0))[0]
            #print cond_TVC
            #print cond_CIC
            print "reliableTracks: ", reliableTracks
            #print type(img), np.size(img), np.shape(img)
            if readFromFile:
                img = cv2.imread(frameName, cv2.IMREAD_COLOR)
            assert img is not None,"Image  file not found at %s" % frameName
            
            for n in reliableTracks:
                bbox = self.__Tracks[n].__getitem__('bbox')
                print "bbox: ", bbox
                trackId   = self.__Tracks[n].__getitem__('id') 
                print "ID: ", trackId
                
                X = bbox[:, 0]
                Y = bbox[:, 1]
                W = bbox[:, 2]
                H = bbox[:, 3]
#                cv2.rectangle(img, (X, Y), (X+W, Y+H), (0,0,255), 2)  #BGR
#                cv2.putText(img,"%d"%trackId, (X, Y), \
#                            cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.8, (255,255,255), 2)
        
           
       #     cv2.line(img, (360,180),(210,450),(255,255,0),2)  #BGR
#            cv2.line(img, (60,200),(200,150),(255,255,0),2)
#            cv2.line(img, (200,150),(200,0),(255,255,0),2)
#            if ~readFromFile: img = img[:, :, (2, 1, 0)]  #convert to RGB
#            cv2.imshow('Mall',img)
#            cv2.imwrite("./tmp/zot_%05d.jpg" % step, img)
#            cv3.waitKey( delay )        #[ms]
                

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#
# ... The demo Tracking PoC
#
def demoTrackingPoC():

    ROI_thresholds = [320, 640, 170, 480]   #[X_left, X_right, Y_top, Y_bottom]
    doTracking = Orchestrator()
     
    for n in range(15):
        BBoxes, frameName = Mall.getMallDetection(n)
        print type(BBoxes), np.shape(BBoxes)
        print "\n\n step:%d -> %s" % (n, frameName)
        doTracking.loadBB(BBoxes)
        
        doTracking.predictNewLocationsOfTracks()
               
        matches, unmatchedTracks, unmatchedDetections = doTracking.detectionToTrackAssignment()
        
        doTracking.updateAssignedTracks(matches)
        
        doTracking.updateUnassignedTracks( unmatchedTracks)
        
        doTracking.deleteLostTracks( ROI_thresholds )
        
        doTracking.createNewTracks(unmatchedDetections)
        
        doTracking.displayTrackingResukts(frameName, n)
        
#
# -----------------------------------------------------------------------
#        
        
def Testing():
#id=-1, bbox=[], hKF=0, age=1, totalVisibleCount=1, consecutiveInvisibleCount=0):
    a1=Track(1, [4, 3, 5], 5, 1, 5, 0)
    a2=Track(2, [6, 3, 4],  6, 1, 1, 0)
    a3=Track(3, [7, 3, 7], 7, 1, 5, 0)
    a4=Track(4, [8, 8, 2], 8, 1, 2, 0)
    a5=Track(4, [8, 8, 2], 8, 1, 2, 0)
    Tr=[]
    print len(Tr), np.size(Tr), np.shape(Tr)
    Tr.append(a1)
    Tr.append(a2)
    Tr.append(a3)
    Tr.append(a4)
    Tr.append(a5)
    print len(Tr), type(Tr)

    print Tr[1].__getitem__('bbox')
    Tr[1].__setitem__('bbox', [44, 34, 55]) 
    print Tr[1].__getitem__('bbox')

    nTracks=len(Tr)
    cond_TVC=np.array([Tr[n].__getitem__('totalVisibleCount') for n in range(nTracks)])
    cond_CIC=np.array([Tr[n].__getitem__('consecutiveInvisibleCount') for n in range(nTracks)])
    print cond_TVC
    print cond_CIC
    reliableTracks=np.where(np.logical_and(cond_TVC>1, cond_CIC==0))[0]
    print reliableTracks, type(reliableTracks)
    print len(reliableTracks)
 
 
    for nn in reliableTracks:
        print 'n-> ', nn, type(nn)
        print Tr[nn].__getitem__('id')


# ================================================================>>>

if __name__ == "__main__":
    demoTrackingPoC()
#    Testing()

 
