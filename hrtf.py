import numpy as np
from pysofaconventions import *
from scipy.spatial import Delaunay
import scipy.signal as sig

class hrtf():
    def __init__(self, CHUNK):
        self.setupHRTF()
        self.overlapAmount = self.FIRs.shape[2]-1 # during convolution, there are "tails" of the digital convolution on either side of the chunk, this is the length
        self.dataPrepend = np.zeros(self.overlapAmount) # the previous chunks trailing tail will be added to the next chunks rising tail
        self.currentTetraIndex = 0 # current convolution tetrahedron
        self.CHUNK = CHUNK

        self._pazpel = [0,0] # convolution point azimuth and elevation in radians
        # self._pel = 0 # convolution point elevation in radians
        px = np.sin(self._pazpel[0])*np.cos(self._pazpel[1])*self.pr
        py = np.cos(self._pazpel[0])*np.cos(self._pazpel[1])*self.pr
        pz = np.sin(self._pazpel[1])*self.pr
        self.pp = np.array([px, py, pz])


    def setupHRTF(self):
        # Paths to sofa files
        # You can download these at https://www.sofaconventions.org/mediawiki/index.php/Files
        # Code should work for any spherically recorded HRTFs
        # This one is included in the resources folder of the repository
        sofaPath = '../_ref/THK_FFHRIR/'
        fileNames = [
            'HRIR_L2702',
            'HRIR_L2702'
        ]

        # Should be noted that the code assumes the software is of the SimpleFreeFieldHRIR standard
        # Not really sure what happens when you use a file that's not of that format...
        sofaFiles = [SOFAFile(sofaPath+fileName+'.sofa','r') for fileName in fileNames]

        # Each source position variable is a list of az, el, r
        sourcePositions = np.concatenate([sofaFile.getVariableValue('SourcePosition')
            for sofaFile in sofaFiles])

        # Turn az and el into radians
        sourcePositions[:,:2] *= np.pi/180

        # We double the surface of points and offset it outwards in order
        # to create a sheath of delaunay tetrahedrons with good aspect ratios.
        # The mean free path is actually just the approximate point to point distance
        # when you speckle points on a sphere, but mean free path sounded cooler.
        meanFreePath = 4*max(sourcePositions[:,2])/np.sqrt(len(sourcePositions))
        sourcePositions[len(sourcePositions)//2:,2] += meanFreePath

        maxR = max(sourcePositions[:,2])-meanFreePath/2
        
        # FIR (Finite Impulse Response) in the form (measurement point index, left IR, right IR)
        FIRs = np.concatenate([sofaFile.getDataIR()
            for sofaFile in sofaFiles])

        # Extract all az, el, r. NOTE: These are in the same order as the sourcePositions list
        az = -np.array(sourcePositions[:,0])
        el = np.array(sourcePositions[:,1])
        r = np.array(sourcePositions[:,2]) 

        az = az + np.random.rand(len(az))/1000
        el = el + np.random.rand(len(el))/1000
        r = r + np.random.rand(len(r))/1000

        xs = np.sin(az)*np.cos(el)*r
        ys = np.cos(az)*np.cos(el)*r
        zs = np.sin(el)*r

        # points is now a list of [x,y,z] in the order of sourcePositions
        points = np.array([xs, ys, zs]).transpose()

        # tri is a delaunay object thingy
        tri = Delaunay(points, qhull_options="QJ Pp")

        # Setup barycentric coordinate calculation
        tetraCoords = points[tri.simplices] # List of tetras' coordinates of points

        T = np.transpose(np.array((tetraCoords[:,0]-tetraCoords[:,3],
                    tetraCoords[:,1]-tetraCoords[:,3],
                    tetraCoords[:,2]-tetraCoords[:,3])), (1,0,2))

        def fast_inverse(A):
            identity = np.identity(A.shape[2], dtype=A.dtype)
            Ainv = np.zeros_like(A)
            planarCount=0
            for i in range(A.shape[0]):
                try:
                    Ainv[i] = np.linalg.solve(A[i], identity)
                except np.linalg.LinAlgError:
                    # If there's a flat object, it's going to create an
                    # infinite value for the inverse matrix (det = 0)
                    # Use this value to help debug geometry
                    planarCount += 1
            # print(planarCount)
            return Ainv

        Tinv = fast_inverse(T) # a list of all the barycentric inverses of T, listed in the same order as the tetras in tri and tetraCoords
        self.tetraCoords = tetraCoords
        self.Tinv = Tinv
        self.tri = tri
        self.FIRs = FIRs
        self.pr = maxR
        return

    def convolveHRIR(self, data):
        gs = self.findTet()

        # interpolate the HRTF associated with pp
        tetVertPos = self.tri.simplices[self.currentTetraIndex]
        hrtfA = self.FIRs[tetVertPos[0],:,:]
        hrtfB = self.FIRs[tetVertPos[1],:,:]
        hrtfC = self.FIRs[tetVertPos[2],:,:]
        hrtfD = self.FIRs[tetVertPos[3],:,:]

        hrtf = hrtfA*gs[0]+hrtfB*gs[1]+hrtfC*gs[2]+hrtfD*gs[3]


        # Now convert the byte data, apply the convolution, and return the byte output
        data_int = np.frombuffer(data, dtype=np.int16)
        data_int = np.concatenate((self.dataPrepend, data_int[0::2]))
        self.dataPrepend = data_int[-self.overlapAmount:]

        # Convolve with the hrtf
        binaural_left = sig.fftconvolve(data_int,hrtf[0])
        binaural_right = sig.fftconvolve(data_int,hrtf[1])

        # Remove Tails
        if len(binaural_left)>0:
            binaural_left = binaural_left[self.overlapAmount:-self.overlapAmount]
            binaural_left = binaural_left.astype(np.int16)

            binaural_right = binaural_right[self.overlapAmount:-self.overlapAmount]
            binaural_right = binaural_right.astype(np.int16)

        # Interleave into stereo byte array
        binaural = np.empty((binaural_left.size + binaural_right.size,), dtype=np.int16)
        binaural[0::2] = binaural_left
        binaural[1::2] = binaural_right
        hrtfData = binaural[:self.CHUNK*2].tobytes()
        return hrtfData

    def findTet(self):
        # finds the target tetra index via inverse barycenter adjacency walk
        # returns the barycentric weightings of the target HRIR point, self.currentTetraIndex stored
        i = 0
        while True:
            [g1, g2, g3] = (self.pp-self.tetraCoords[self.currentTetraIndex,3])@self.Tinv[self.currentTetraIndex]
            g4 = 1-g1-g2-g3
            gs = [g1, g2, g3, g4]
            if all(g >= 0 for g in gs):
                return gs
            if i>=len(self.tetraCoords):#20000
                raise ValueError('Searched all possible tets, something went wrong')
            self.currentTetraIndex = self.tri.neighbors[self.currentTetraIndex][gs.index(min(gs))]
            i+=1


    @property
    def pazpel(self):
        return self._pazpel
    
    @pazpel.setter
    def pazpel(self, value):
        self._pazpel = value
        px = np.sin(self._pazpel[0])*np.cos(self._pazpel[1])*self.pr
        py = np.cos(self._pazpel[0])*np.cos(self._pazpel[1])*self.pr
        pz = np.sin(self._pazpel[1])*self.pr
        self.pp = np.array([px, py, pz])