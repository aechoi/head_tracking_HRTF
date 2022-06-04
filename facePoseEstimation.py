import cv2
import math
import mediapipe as mp
import time
from threading import Thread
from webcamVideoStream import webcamVideoStream

class facePoseEstimation():
    """docstring for facePoseEstimation"""
    def __init__(self, est='face', ):
        self.vs = webcamVideoStream(0)
        self.vs.start()

        if est=='pose':
            self.mpPose = mp.solutions.pose
            self.pose = self.mpPose.Pose()
            self.indREar = 8
            self.indREyeO = 6
            self.indLEar = 7
            self.indLEyeO = 3

        if est=='face':
            self.mpFace = mp.solutions.face_detection
            self.face = self.mpFace.FaceDetection()

            # 0 - left eye
            # 1 - right eye
            # 2 - nose
            # 3 - mouth
            # 4 - left ear
            # 5 - right ear
            self.indREar = 5
            self.indREyeO = 1
            self.indLEar = 4
            self.indLEyeO = 0

        self.mpDraw = mp.solutions.drawing_utils

        self.est = est

        self.pTime = 0
        self.firstTime = True

        self.az = 0
        self.el = 0

        self.calEl = 0
        self.calAz = 0

        self.fps=0
        while self.calEl==0 and self.calAz==0:
            self.calibrate()
        self.stopped = False
        
    def start(self):
        Thread(target=self.cyclePose, args=()).start()
        return self

    def fastInterp(self, val, ilo, ihi, olo, ohi):
        return (val-ilo)/(ihi-ilo)*(ohi-olo)+olo

    def earEyeDiffDeriv(self, keypts, cal=False):
        REarX, REarY = keypts[self.indREar].x, keypts[self.indREar].y
        REyeOX, REyeOY = keypts[self.indREyeO].x, keypts[self.indREyeO].y
        LEarX, LEarY = keypts[self.indLEar].x, keypts[self.indLEar].y
        LEyeOX, LEyeOY = keypts[self.indLEyeO].x, keypts[self.indLEyeO].y

        imgel = (REarY-REyeOY + LEarY-LEyeOY)/2
        imgaz = REyeOX - REarX + LEyeOX - LEarX

        if cal:
            return imgaz, imgel
        el = self.fastInterp(imgel-self.calEl, -0.03, 0.04, 120, 50)
        az = self.fastInterp(imgaz-self.calAz, -0.1, 0.1, 50, 140)

        return az, el

    def posAzEl(self, bbox):
        centerX = bbox.xmin + bbox.width/2
        centerY = bbox.ymin + bbox.height/2

        az = self.fastInterp(centerX, 0,1, -225,225)
        el = self.fastInterp(centerY, 0.2,0.8, 70,-70)

        return az, el

    def calibrate(self):
        img = self.vs.read()
        img = cv2.flip(img, 1)

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if self.est == 'pose':
            results = self.pose.process(imgRGB)
            if results.pose_landmarks:
                self.mpDraw.draw_landmarks(img, results.pose_landmarks, self.mpPose.POSE_CONNECTIONS)
                res = results.pose_landmarks.landmark
                self.calAz, self.calEl = self.earEyeDiffDeriv(res, cal=True)            

        elif self.est == 'face':
            results = self.face.process(imgRGB)
            if results.detections:
                for detection in results.detections:
                    self.mpDraw.draw_detection(img, detection)
                    bbox = detection.location_data.relative_bounding_box # xmin, ymin, width, height
                    keypts = detection.location_data.relative_keypoints # x, y as %
                    self.calAz, self.calEl = self.earEyeDiffDeriv(keypts, cal=True)
                    # break
        return

    def cyclePose(self):
        while True:
            if self.stopped:
                return
                
            img = self.vs.read()
            img = cv2.flip(img, 1)
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            if self.est == 'pose':
                results = self.pose.process(imgRGB)
                if results.pose_landmarks:
                    self.mpDraw.draw_landmarks(img, results.pose_landmarks, self.mpPose.POSE_CONNECTIONS)
                    res = results.pose_landmarks.landmark
                    self.az, self.el = self.earEyeDiffDeriv(res)

            elif self.est == 'face':
                results = self.face.process(imgRGB)
                if results.detections:
                    for detection in results.detections:
                        self.mpDraw.draw_detection(img, detection)
                        bbox = detection.location_data.relative_bounding_box # xmin, ymin, w, h
                        keypts = detection.location_data.relative_keypoints # x, y as %
                        # self.az, self.el = self.earEyeDiffDeriv(keypts)
                        self.az, self.el = self.posAzEl(bbox)
                        # break

            cTime = time.time()
            try:
                newfps = 1/(cTime-self.pTime)
            except(ZeroDivisionError):
                newfps = self.fps
            self.fps = .99*self.fps + .01*newfps 
            self.pTime = cTime

            cv2.putText(img, f'fps: {int(self.fps)}', (50,50), cv2.FONT_HERSHEY_PLAIN, 3,
                (255, 0, 0), 3)
            cv2.putText(img, f'az: {int(self.az)}', (50,100), cv2.FONT_HERSHEY_PLAIN, 3,
                (255, 0, 0), 3)
            cv2.putText(img, f'el: {int(self.el)}', (50,150), cv2.FONT_HERSHEY_PLAIN, 3,
                (255, 0, 0), 3)
            cv2.imshow('img', img)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.calibrate()

    def read(self):
        return self.az, self.el

    def stop(self):
        self.stopped = True
        self.vs.stop()

def main():
    fpe = facePoseEstimation()
    az, el = 0, 0
    while True:
        az, el = fpe.cyclePose()
if __name__ == '__main__':
    main()