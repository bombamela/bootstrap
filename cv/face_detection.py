import cv2
import numpy as np
import time


class FaceTracker(object):
    """A tracker for facial features: face,eyes,nose,mouth"""

    def __init__(self, scale_factor=1.2, min_neighbors=2, flags=cv2.cv.CV_HAAR_SCALE_IMAGE):
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.flags = flags

        self.face_rects = []
        self._face_classifier = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')

    def update(self, image):
        """Update the tracked facial features"""

        self.face_rects = []

        if is_gray(image):
            image = cv2.equalizeHist(image)

        else:
            image = cv2.cvtColor(image, cv2.cv.CV_BGR2GRAY)
            cv2.equalizeHist(image, image)

        min_size = width_height_divided_by(image, 8)
        face_rects = self._face_classifier.detectMultiScale(image,
                                                            self.scale_factor,
                                                            self.min_neighbors,
                                                            self.flags,
                                                            min_size)
        self.face_rects = face_rects

    def draw_debug_rects(self, image):
        """Draw rectangles around the tracked facial features"""

        if is_gray(image):
            face_color = 255

        else:
            #face_color = (255, 255, 255)  # white
            face_color = (0, 255, 0)  # green

        for face in self.face_rects:
            outline_rect(image, face, face_color)


class CaptureManager(object):
    def __init__(self, capture, should_mirror_preview=False):

        self.should_mirror_preview = should_mirror_preview

        self._capture = capture
        self._channel = 0
        self._entered_frame = False
        self._frame = None
        self._frames_elapsed = long(0)
        self._fps_est = None

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self):
        return self._channel

    @property
    def frame(self):
        if self._entered_frame and self._frame is None:
            _, self._frame = self._capture.retrieve(channel=self.channel)
        return self._frame

    def enter_frame(self):
        # capture the next frame

        assert not self._entered_frame, 'previous enter_frame() had no matching exit_frame()'
        if self._capture is not None:
            self._entered_frame = self._capture.grab()

    def exit_frame(self):
        # draw to window, write to files, release the frame

        # frame is retrievable or not
        if self.frame is None:
            self._entered_frame = False
            return

        if self._frames_elapsed == 0:
            self._start_time = time.time()
        else:
            time_elapsed = time.time() - self._start_time
            self._fps_est = self._frames_elapsed / time_elapsed
        self._frames_elapsed += 1

        if self.should_mirror_preview:
            mirrored_frame = np.fliplr(self._frame).copy()

        # release the frame
        self._frame = None
        self._entered_frame = False


def outline_rect(image, rect, color):
    if rect is None:
        return

    x, y, w, h = rect
    cv2.rectangle(image, (x, y), (x+w, y+h), color)


def is_gray(image):
    """Return true if the image has one channel per pixel"""
    return image.ndim < 3


def width_height_divided_by(image, divisor):
    """Return an images dimensions, divided by a value"""
    h, w = image.shape[:2]
    return w / divisor, h / divisor