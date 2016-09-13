#  track_v06.py
#  
#  Copyright 2015 elf <hduser@JASMINE>
#  
# 12.05.2016 
#
import numpy as np
import cv2
import KalmanFilterObj_v2 as KFO
from collections import deque
import math
from sympy.geometry import Ellipse,Point
from time import sleep

#
# ... Track structure definition
#
class Track(object):
    def __init__(self,  id_=-1, bbox=[], hKF=0,color=(0,255,255), age=1, totalVisibleCount=1, consecutiveInvisibleCount=0):
        self.id = id_
        self.bbox = np.matrix(bbox)
        self.kalmanFilter = hKF
        self.age = age
        self.totalVisibleCount = totalVisibleCount
        self.consecutiveInvisibleCount = consecutiveInvisibleCount
        self.tracklet = deque(5*[[-1,-1]],5)
        self.color = color
        
        
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
class Orchestrator( object ):

    def __init__(self,  VERBOSE=False ):
        self.__Tracks = []
        self.__Centroids = []
        self.__BBoxes = []
        self.__nextTrackId=1
        self.VERBOSE=VERBOSE
        self.configParams = {}
  
    def loadBB(self, BBoxes):
        # Definitio BBox : [Xo, Yo, W, H]
        self.__BBoxes = BBoxes
        self.__Centroids = BBoxes[:, 0:2] + BBoxes[:, 2:4]*0.5   
        

    """
    
    """      
    def predictNewLocationsOfTracks(self):
        nTracks = len(self.__Tracks)
        if self.VERBOSE: print "%% predictNewLocations for the existing (%d) tracks" % nTracks
                
        for n in range(nTracks):
            TT = self.__Tracks[n]
            trackID = TT.__getitem__('id') 
            bbox    = TT.__getitem__('bbox')
            hKF     = TT.__getitem__('kalmanFilter')
            hKF.kf_predict()
             
            predictedCentroid = hKF.X[0:2].T  
            newbbox = np.matrix(np.hstack((predictedCentroid - bbox[:, 2:4]*0.5, bbox[:, 2:4])))
            self.__Tracks[n].__setitem__('bbox', newbbox)
                                    
            predictedCentroid = np.asarray( predictedCentroid, dtype=np.int32 ).reshape(-1)
            print "Predicted trackID: ", trackID, predictedCentroid
            theTracklet = TT.__getitem__('tracklet')
            theTracklet.append([predictedCentroid[0],predictedCentroid[1]])
            print theTracklet
        
    """
    
    """     
    def detectionToTrackAssignment(self, costUnassignedTracks = 60):        
        nTracks = len(self.__Tracks)
        if self.VERBOSE: print "%% detectionToTrackAssignment for existing %d tracks for cost=%d" % (nTracks,costUnassignedTracks)
        
        nDetections = self.__Centroids.shape[0] 
        if self.VERBOSE: print "Found nTracks:%d nDetection:%d" % (nTracks, nDetections)
        
        cost = np.matrix( np.zeros((nTracks, nDetections)))
        
        for n in range( nTracks):
            print "TrackID: %d [%d]" % (self.__Tracks[n].__getitem__('id'), n)
            hKF = self.__Tracks[n].__getitem__('kalmanFilter')
            cost[n,:] = hKF.kf_distance( self.__Centroids.T )
             
        Regular, LostTracks, NewDetections = KFO.assignDetectionsToTracks(cost, costUnassignedTracks)
        print "[M, UT, UD]: \n",  Regular.T, LostTracks, NewDetections
        
        #Regular2, LostTracks2, NewDetections2 = KFO.DetectionsToTracks(cost)
        #print "[M++, UT+, UD+]: \n", Regular2.T, LostTracks2, NewDetections2
         
        return Regular, LostTracks, NewDetections

    """
              
    """       
    def updateAssignedTracks(self, Regular):
         
        nAssignedTracks = len(Regular)
        if self.VERBOSE: print "%% updateAssignedTracks: %d" % nAssignedTracks
        
        for n in range(nAssignedTracks):
            tid = Regular[n, 0]   
            TT = self.__Tracks[tid]
            trackID = TT.__getitem__('id')
            if self.VERBOSE: print "Regular Track ID: %d: " % ( trackID )
                     
            detectionId = Regular[n, 1]
            
            centroid = self.__Centroids[detectionId, :]
            bbox     = self.__BBoxes[detectionId, :]
            
            hKF = TT.__getitem__('kalmanFilter')            
            hKF.kf_update( centroid.T )
            
            TT.__setitem__('bbox', bbox)           
            age = TT.__getitem__('age')
            TT.__setitem__('age', age+1)
        
            totalVisibleCount = TT.__getitem__('totalVisibleCount')
            TT.__setitem__('totalVisibleCount', totalVisibleCount+1)        
            TT.__setitem__('consecutiveInvisibleCount', 0 )
            
            centroid = np.asarray( centroid, dtype=np.int32 ).reshape(-1)
            theTracklet = TT.__getitem__('tracklet')
            
            # replace predicted BB with detectected BB
            print "Updated trackID: ", trackID, centroid
            theTracklet.pop()
            theTracklet.append([centroid[0],centroid[1]])
            print theTracklet
     
            
    """
    
    """         
    def updateUnassignedTracks(self, LostTracks):   #LOST Tracks
        nLostTracks = len(LostTracks)
        if self.VERBOSE: print "%% updateLostTracks %d" % nLostTracks
        
        for n in range(nLostTracks):
            tid = LostTracks[n]
            TT = self.__Tracks[tid]
            trackID = TT.__getitem__('id')
            if self.VERBOSE: print "Lost Track ID: %d: " % ( trackID)
            
            age = TT.__getitem__('age')
            TT.__setitem__('age', age+1)
            
            consecutiveInvisibleCount = TT.__getitem__('consecutiveInvisibleCount')
            TT.__setitem__('consecutiveInvisibleCount', consecutiveInvisibleCount+1)
                     
    """
       
    """
    def deleteLostTracks(self, ROI_Threshold, CIC_Threshold, step):
        # ROI_thresholds = [X_l, X_r, Y_t, Y_b]
        
        if self.VERBOSE: print "%% deleteLostTracks"
        
        nTracks = len(self.__Tracks)
        if nTracks > 0:
            delindex = []
            
            # (1) check if outside ROI
            # (2) otherside if has been invisible for more than CIC_Threshold cycles
            for n in range( nTracks ):
                TT = self.__Tracks[n]
                trackID = TT.__getitem__('id')
            
                hKF = TT.__getitem__('kalmanFilter') #get value computed after kf_update()
                   
                age = TT.__getitem__('age')
                CIC = TT.__getitem__('consecutiveInvisibleCount')
                Visibility = TT.__getitem__('totalVisibleCount') / (age+0.1)          
                #print trackID, age, CIC, Visibility, (age < 10 and Visibility < 0.5 )
                #print isOutsideROI( ROI_Threshold, hKF.X ), hKF.X
                if isOutsideROI( ROI_Threshold, hKF.X ) or \
                    (CIC > CIC_Threshold) or (age < 10 and Visibility < 0.5 ) :
                    delindex.append(n)                   
                                                  
            # Delete lost tracks
            if delindex:
                #print delindex
                for o,d in enumerate(delindex):
                    d -= o
                    if self.VERBOSE: print "DELETE TrackID=%d\n" % (self.__Tracks[d].id)
                    del self.__Tracks[d]
                    
    """
    This function create a new Track object assigned to a new detected BB
    """                                               
    def createNewTracks(self, NewDetections, step):
        newColor = [(255,0,0)  ,(0,255,0)  ,(0,0,255)    ,(255,255,0), \
                    (0,255,255),(255,0,255),(255,255,255),(0,0,0)]
        nTracks = len(self.__Tracks)    
        if self.VERBOSE:  print "%% createNewTracks:  there are %d tracks" % nTracks
        
        for n in NewDetections:
            centroid = self.__Centroids[n, :]
            bbox     = self.__BBoxes[n, :]
            
            
            """
             if a new track is initialized withing the ellisse with origin in the frame center
             and semiaxis a=320-DMZ and b=240-DMZ then the track is a ghoist and shall be deleted
            """ 
            DMZ = 60
            cx = np.asarray( centroid, dtype=np.int32 ).reshape(-1)     
            el = Ellipse(Point(320,240),240-DMZ,320-DMZ)
            if el.encloses_point(Point(cx[0],cx[1])) and (step > 3):
                print "GHOST: ", centroid
                return      
            
            """
            set initial velocoties dependending of the side of entrance
            """
            if cx[1] < DMZ :
                Vo = np.array([[0,10]])
            elif cx[1] > 480-DMZ :
                Vo = np.array([[0,-10]])
            elif cx[0] < DMZ :
                Vo = np.array([[10,0]]) 
            elif cx[0] > 640 - DMZ :
                Vo = np.array([[-10,0]])    
            else:
                Vo = np.array([[0, 0]])                 
                
            initialGuess = np.hstack((centroid, Vo))
            if self.VERBOSE: print "Initial Guess: ", initialGuess
            kalmanFilter = KFO.KalmanFilterObj(initialGuess, [100, 100], [0, 0, 100, 50], [100, 100, 100, 100], 1)
            newTrack = Track(self.__nextTrackId, bbox, kalmanFilter, newColor[ self.__nextTrackId % 7] )
            
            theTracklet = newTrack.__getitem__('tracklet')
            
            for _ in range(5): theTracklet.append([cx[0],cx[1]])
            if self.VERBOSE: print "ONCE: ", self.__nextTrackId, theTracklet
            
            self.__Tracks.append(newTrack)
            self.__nextTrackId += 1
            
    """
    
    """         
    def displayTrackingResults(self, frameName, step, image, outpipe, frameCounter, delay=1000 ):
        
        if self.VERBOSE: print "%% DISPLAY == %s" % frameName
               
        minVisibleCount=2
        overlay = image.copy()       
        
        if self.__Tracks:   
            nTracks = len(self.__Tracks)
                                        
            if self.VERBOSE:
                print 'id \t age \t totalvisibleCount \t consecutiveInvisibleCount'
                for nn in range(nTracks):
                    TT = self.__Tracks[nn]
                    print TT.__getitem__('id'),TT.__getitem__('age'),TT.__getitem__('totalVisibleCount'),TT.__getitem__('consecutiveInvisibleCount')
            
            cond_TVC=np.array([self.__Tracks[n].__getitem__('totalVisibleCount') for n in range(nTracks)])            
            reliableTracks = np.where( cond_TVC>minVisibleCount )[0]  
            print "reliableTracks: ", reliableTracks          
                                           
            if self.VERBOSE: # Green block in the centroid
                for n in range(len( self.__Centroids )):   
                    centroid = self.__Centroids[n, :]
                    centroid = np.asarray( centroid, dtype=np.int32 ).reshape(-1)
                    Zx=centroid[0];  Zy=centroid[1]
                    cv2.rectangle(overlay, (Zx,Zy),(Zx+6,Zy+6),(0,255,0),-4)  
                    
        
            for n in reliableTracks:
                TT = self.__Tracks[n]
                trackID   = TT.__getitem__('id') 
                if self.VERBOSE: print "Display Track ID: %d [%d]: " % ( trackID, n )
                               
                bbox = np.asarray( TT.__getitem__('bbox'), dtype=np.int32 ).reshape(-1)                                                   
                X = bbox[0];  Y = bbox[1];  W = bbox[2]; H = bbox[3]

                # display trackID for each tracklet
                if self.VERBOSE: cv2.putText(overlay,"%d"%trackID, (X, Y),  cv2.FONT_HERSHEY_COMPLEX_SMALL, 2, (255,255,0), 3)
                       
                theTracklet = TT.__getitem__('tracklet')
                theColor = TT.__getitem__('color')
               
                # set tracklet color to black if it is only predicted
                if TT.__getitem__('consecutiveInvisibleCount') > 0:
                    theColor = (0,0,0)                     
               
                if self.VERBOSE:  print theTracklet
                thePoints = np.array( [ tea for tea in theTracklet ])  
                drawTracklet( overlay, thePoints, theColor, 7 , 6)
                                
                if self.VERBOSE:  cv2.rectangle(overlay,(X, Y), (X+int(W), Y+int(H)), (255,0,0), 2)  #BGR
                
					
        opacity = 0.4
        #cv2.putText(overlay, frameName, (10,80), cv2.FONT_HERSHEY_COMPLEX_SMALL, 2, (255,255,0), 3)
        if (frameCounter >= 37 and frameCounter <= 42) or (frameCounter >= 54 and frameCounter <= 60)or (frameCounter >= 66 and frameCounter <= 75) or (frameCounter >= 105 and frameCounter <= 115) or (frameCounter >= 137 and frameCounter <= 142) or (frameCounter >= 156 and frameCounter <= 159):
            cv2.rectangle(overlay,(350,0),(480,480),(0,0,255),-1)
        else:
            cv2.rectangle(overlay,(350,0),(480,480),(0,255,0),8)

        cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)   
                       
        #image = image[:, :, (2, 1, 0)]  #convert to RGB
        ret, jpeg = cv2.imencode(".jpg", image)                           
      #  cv2.imwrite(outpipe,image)
        f = open(outpipe,'wb',0)
        f.write(jpeg)
        f.close()
        sleep(0.3)
        return 
        
 
# -----------------------------------------------------------------------------------------
# .... Helpers
"""


"""
def getCentroidFromBB( BB ):
    centroid = hKF.X[0:2].T - bbox[:, 2:4]/2 
    return centroid


"""                    

"""
def isOutsideROI( ROI_Threshold, X  ):
    XL = ROI_Threshold[0] ; XR= ROI_Threshold[1];
    YT = ROI_Threshold[2] ; YB= ROI_Threshold[3];
    
    Yu=X[1]; Xu=X[0]; Vxu=X[2]; Vyu=X[3]; 
    
    if ((Yu < YT ) and (Vyu < 0.0)) or ((Xu < XL ) and (Vxu < 0.0)) or \
                    ((Yu > YB ) and (Vyu > 0.0)) or ((Xu > XR ) and (Vxu > 0.0)):
        return True
    else:
        return False
        


def drawArrow(img, points, base, color):
    x1=points[3][0]; y1=points[3][1]
    x2=points[4][0]; y2=points[4][1]
    
    if y2 == y1:
        triangle = np.array([[x1,y1+base],[x1,y1-base],[x2,y2]])
    else:
        m  = (x2 - x1)/(y2 - y1)
        xt = base/math.sqrt(1.+m*m); 
        triangle = np.array([[xt+x1,-m*xt + y1],[-xt+x1,m*xt+y1],[x2,y2]])  
         
    triangle = triangle.astype(int) 
    cv2.fillPoly(img, [triangle], color )  
    
"""
    This is an helper function to draw an arrowed tracklet
    img :  the destination image
    thePoints : an array of (5) points coordinates
    the Color : the RGB color 
    tw : the tracklet width
    aw : the arrow width from the border of the tracklet
         This means that aw=0 is an arrow originating from the tracklet border
         that will be drawn as a triangle of base (tw) and vertex on the 5th
         points coordinates
"""    
def drawTracklet( img, thePoints, theColor, tw, aw ):
    cv2.polylines(img, [thePoints[0:4]], False, theColor, tw )     
    drawArrow(img, thePoints, int(tw*0.5+aw), theColor)     
 
 
def drawTrackletEx(img, thePoints, theColor, tw, aw):
    x0=thePoints[0][0]; y0=thePoints[0][1]
    x1=thePoints[1][0]; y1=thePoints[1][1]
    x3=thePoints[3][0]; y3=thePoints[3][1]
    x4=thePoints[4][0]; y4=thePoints[4][1]
       
    base = int(tw*0.4 + 0.5)
    if y0 == y1:
        tail = np.array([[x0,y0+base],[x0,y0-base]])
    else:
        m  = (x1 - x0)/(y1 - y0)
        xt = base/math.sqrt(1.+m*m); 
        tail = np.array([[xt+x0,-m*xt + y0],[-xt+x0,m*xt+y0]])  
    
    base = int(tw*0.5 + 0.5)
    if y3 == y4:
        head = np.array([[x3,y3+base],[x3,y3-base]])
    else:
        m  = (x4 - x3)/(y4 - y3)
        xt = base/math.sqrt(1.+m*m); 
        head = np.array([[xt+x3,-m*xt + y3],[-xt+x3,m*xt+y3]])  
    
    trapez = np.vstack((tail, head))     
    trapez = trapez.astype(int) 
    cv2.fillPoly(img, [trapez], theColor )   
 
    drawArrow(img, thePoints, int(tw*0.5+aw), theColor) 
 
 
