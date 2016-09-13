import numpy as np
from scipy.linalg import expm
from scipy.spatial.distance import mahalanobis
from sys import maxint
from munkres import Munkres, print_matrix
import lapjv as lap
#import laph0 as laph
import warnings
from scipy.linalg import toeplitz
import math

class KalmanFilterObj(object):
    def __init__(self, InitialGuess, MeasurementNoise, ProcessNoise, StateCovariance, dt=1):
          
        self.X  = np.matrix(InitialGuess).T            #  Initial Guess= [ Xo, Yo, Vxo, Vyo]
        #print 'M ', self.X
        self.P  = np.matrix(np.diag(StateCovariance))  # StateCovariance = [200, 50, 200, 50]
        #print 'P ', self.P
        self.Q = np.matrix(np.diag(ProcessNoise))      # ProcessNoise = [0, 0, 100, 25]
        #print 'Q1 ', self.Q
        self.R = np.matrix(np.diag(MeasurementNoise))  # MeasurementNoise  [100, 100]
        #print 'R ', self.R
        self.Z = self.X
        self.__H = np.matrix('''1 0 0 0; 0 1 0 0''')
        F = np.matrix('''0 0 1 0; 0 0 0 1; 0 0 0 0; 0 0 0 0''')

        self.__lti_discrete(F, dt)
        #print 'A  Q2 ', self.__A, self.Q
    """

    """
    def kf_predict(self): 

        # x = A*x 
        self.X = self.__A * self.X

        # P = A*P*A' + Q
        self.P = self.__A * self.P * (self.__A).T + self.Q
        
        Zp = self.__H * self.X; 
        Xp = self.X
        Pp = self.P
        
        return (Zp,Xp,Pp)
    """

    """
    def kf_update(self, Measurement ):
        #print 'Y: ',Measurement
        assert Measurement.shape[0]==2,"We have a problem in kf_update()"
        
        IM=self.__H * self.X                           #mean of predictive distribution of Y
        #print 'IM ',IM
        IS=self.R + self.__H * self.P * self.__H.T     #covariance of predictive mean of Y
        #print 'IS ',IS
        K = self.P * self.__H.T * IS.I                 #kalman gain
        #print 'K ', K
        self.X = self.X + K * (Measurement - IM)       #updated state mean
        self.Y = Measurement
        self.P = self.P - K * IS * K.T                 #updated state covariance
        
        #print 'M= ',self.X
        #print 'P= ',self.P
        
        Zc = self.__A * self.X;   self.Z=Zc
        Xc = self.X
        Pc = self.P
        
        return (Zc,Xc,Pc)
    """
    
    """   
    def __lti_discrete(self, F, dt ):

        Q = self.Q
       
        n = F.shape[0]
        self.__A = np.matrix(expm(F*dt))

        phi = np.zeros((2*n, 2*n))

        phi[0:n,     0:n] = F
        phi[0:n,   n:2*n] = Q
        phi[n:2*n, n:2*n] = -F.T

        zo = np.vstack((np.zeros((n,n)), np.eye(n)))
        CD = np.matrix(expm(phi*dt)) * np.matrix(zo)

        C = CD[0:n,:]
        D = CD[n:2*n,:]
        self.Q = C * D.I

    """
        
    """     
    def kf_distance(self, Detections): 
        # Detections == Centroids detected on a new frame
        assert Detections.shape[0]==2,"Detections matrix shall be transposed"
        
        Predictions  = self.__H * self.X
        Vxp=self.X[2]; Vyp=self.X[3];
        alpha = math.atan2(Vyp,Vxp)
          
        numPredictions = Predictions.shape[1]
        numDetections  =  Detections.shape[1]
        
        cost  = np.zeros((numPredictions, numDetections))
        Delta = Detections - np.tile(Predictions, numDetections)        
        cost  = np.sqrt(np.diag((Delta.T * Delta).T))
        
        return np.matrix(cost)

 
"""
 This function resolve the LAP for assigning Tacks to Detections using a cost function reperesnting the L2 distance
 between a track postion prediction and all the available detections.
"""
def assignDetectionsToTracks( cost, costUnassignedTracks, costUnassignedDetections=0):
   
    cols = cost.shape[1]
    rows = cost.shape[0]     
            
    if costUnassignedDetections==0: costUnassignedDetections = costUnassignedTracks
       
    maxCost = 10E5  #maxint    
    paddedSize = np.maximum(2,rows + cols)     #elf 040216 - bug fix when nobody home

    if rows== 0 or cols==0:
        padCost= np.ones((paddedSize,paddedSize))*maxCost
    else:   
        B = toeplitz( np.hstack((costUnassignedTracks, [maxCost for _ in range(rows-1)])))    
        C = toeplitz( np.hstack((costUnassignedDetections, [maxCost for _ in range(cols-1)]))) 
        D = np.zeros((cols, rows))        
        padCost = np.bmat([[cost,B], [C,D]])  
    
    #print_matrix(padCost.tolist() )
       
    if 1==0:
        m = Munkres()
        tmpz = np.copy(padCost)
        matchesList = m.compute( tmpz )
        matches = np.array(matchesList)
        rowInds = matches[:,0]  
        colInds = matches[:,1]  
    else:
        z,colInds,y = lap.lap(padCost)
        rowInds=np.asarray(range(paddedSize))
        matches=np.vstack((rowInds,colInds)).T
       
    mask1 = np.logical_and(rowInds<rows,colInds>=cols)
    mask2 = np.logical_and(colInds<cols,rowInds>=rows)
    mask3 = np.logical_and(rowInds<rows,colInds<cols)
    
    unmatchedTracks     = rowInds[np.nonzero(mask1)]  
    unmatchedDetections = colInds[np.nonzero(mask2)]
    matches = matches[np.nonzero(mask3)]
        
    return matches, unmatchedTracks, unmatchedDetections


######################################################################################

def testHung():
    print "====inside testHung====="
    hKF0=KalmanFilterObj([1, 2, 0.5, 0.5], [0.1, 0.1], [0 ,0 ,0.1, 0.1], [0.1, 0.1, 0.1 ,0.1], 0.1)
    cost = hKF0.kf_distance(np.matrix('''1 2; 3 4; 5 6''').T )
    costMatrix = np.zeros((2,3))
    costMatrix[0,:]=cost
    costMatrix[1,:]=cost
    costMatrix = np.matrix('''0.14142   1.55563   2.06155;
                              1.27279   0.14142   1.11803''')
    print costMatrix
  
     
    assignments, unassignedTracks, unassignedDetections = assignDetectionsToTracks(costMatrix,0.2) 
    print  assignments, unassignedTracks, unassignedDetections
     
        
def testKF():  
    Y1=np.matrix('''1.31266   1.14787   1.34464   0.96440   1.08998;
                1.84368   1.72939   2.89591   1.97160   2.62979''')

    Y2=np.matrix('''9.6415    9.8238    9.8104    9.9663    9.8266;
                10.5988    9.9981    9.3334    9.8379    9.1233''')

 
    hKF0=KalmanFilterObj([1, 2, 0.5, 0.5], [0.1, 0.1], [0 ,0 ,0.1, 0.1], [0.1, 0.1, 0.1 ,0.1], 0.1)
    #hKF1=KalmanFilterObj([1,2,3,4],[100,50],[0, 0, 100, 25],[200,50,200,50],10)
    cost = hKF0.kf_distance(np.matrix('''1 2; 3 4; 5 6''').T )
    print 'cost= ',cost

    for n in range(5):  
        hKF0.kf_predict()
        hKF0.kf_update(Y1[:,n] ) 
        print 'Y ',Y1[:,n],' X: ', hKF0.X[0:2].T



if __name__ == "__main__":
    testHung()
    
