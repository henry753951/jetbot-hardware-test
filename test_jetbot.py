"""Small check: motor order/stop and CSI fallback/release."""

from jetbot_remote import find_camera, test_motors


class Robot:
    def __init__(self):
        self.calls = []

    def forward(self, speed):
        self.calls.append(("forward", speed))

    def left(self, speed):
        self.calls.append(("left", speed))

    def right(self, speed):
        self.calls.append(("right", speed))

    def stop(self):
        self.calls.append(("stop",))


robot = Robot()
test_motors(robot, 0.2, sleep=lambda _: None)
assert robot.calls == [
    ("forward", 0.2), ("stop",),
    ("left", 0.2), ("stop",),
    ("right", 0.2), ("stop",),
    ("stop",),
]


class Camera:
    def __init__(self, opened):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return True, object()

    def release(self):
        self.released = True


class CV2:
    CAP_GSTREAMER = 1

    def __init__(self):
        self.cameras = []

    def VideoCapture(self, pipeline, backend):
        camera = Camera("sensor-id=1" in pipeline)
        self.cameras.append(camera)
        return camera


cv2 = CV2()
camera, sensor_id = find_camera(cv2, sleep=lambda _: None)
assert sensor_id == 1 and camera is cv2.cameras[1]
assert cv2.cameras[0].released and not camera.released
camera.release()
print("Motor sequence and CSI fallback OK")
