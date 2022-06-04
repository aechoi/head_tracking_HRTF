from threading import Thread
import cv2
import time

class webcamVideoStream():
    """docstring for webcamVideoStream"""
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        # self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # self.fps = 20.0
        # self.out = cv2.VideoWriter('output.avi', self.fourcc, self.fps, (1920, 1080))
        # self.lastFrameTime = time.time()
        self.ret, self.img = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                try:
                    # self.cap.stop()
                    self.cap.release()
                    cv2.destroyAllWindows()
                except:
                    print("\nyou shouldn't be able to see this error message... but it's probably fine lol\n")
                return
            # otherwise, read the next frame from the stream
            self.ret, self.img = self.cap.read()
            # if time.time()-self.lastFrameTime > 1/self.fps:
            #     self.out.write(self.img)
            #     self.lastFrameTime = time.time()


    def read(self):
        # return the frame most recently read
        return self.img

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True