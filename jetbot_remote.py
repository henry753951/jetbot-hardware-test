"""Runs in the JetBot's Jupyter container (Python 3.6)."""

import argparse
import glob
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


def test_motors(robot, speed, sleep=time.sleep):
    try:
        for label, move in (("Forward", robot.forward), ("Left", robot.left), ("Right", robot.right)):
            print("Motor: {} at speed {} for 1 second".format(label, speed), flush=True)
            move(speed)
            sleep(1)
            robot.stop()
            print("Motor: {} command complete; stopped".format(label), flush=True)
            sleep(0.3)
    finally:
        robot.stop()
        print("Motor: final stop sent", flush=True)


def find_camera(cv2, sleep=time.sleep):
    for sensor_id in (0, 1):
        print("Camera: testing CSI {}".format(sensor_id), flush=True)
        pipeline = (
            "nvarguscamerasrc sensor-id={} ! "
            "video/x-raw(memory:NVMM),width=816,height=616,format=NV12,framerate=30/1 ! "
            "nvvidconv ! video/x-raw,width=300,height=300,format=BGRx ! "
            "videoconvert ! video/x-raw,format=BGR ! appsink drop=true max-buffers=1"
        ).format(sensor_id)
        camera = None
        keep = False
        try:
            camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if camera.isOpened():
                for _ in range(10):
                    ok, frame = camera.read()
                    if ok and frame is not None:
                        print("Camera: CSI {} working".format(sensor_id), flush=True)
                        keep = True
                        return camera, sensor_id
                    sleep(0.2)
            print("Camera: CSI {} returned no image".format(sensor_id), flush=True)
        except Exception as exc:
            print("Camera: CSI {} failed: {}".format(sensor_id, exc), flush=True)
        finally:
            if camera is not None and not keep:
                camera.release()
    return None, None


def serve_preview(camera, sensor_id, cv2, port):
    class Preview(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.end_headers()
                return
            if self.path == "/":
                content = (
                    "<h1>JetBot camera preview</h1>"
                    + ("<p>CSI {}</p><img src='/stream' width='600'>".format(sensor_id)
                       if camera is not None else
                       "<p>No CSI camera detected. Check the ribbon cable and restart the JetBot.</p>")
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            if self.path != "/stream" or camera is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                while True:
                    ok, frame = camera.read()
                    if not ok:
                        print("Camera: stream stopped; no frame", flush=True)
                        break
                    encoded_ok, jpeg = cv2.imencode(".jpg", frame)
                    if not encoded_ok:
                        continue
                    data = jpeg.tobytes()
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write("Content-Length: {}\r\n\r\n".format(len(data)).encode("ascii"))
                    self.wfile.write(data + b"\r\n")
                    self.wfile.flush()
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = HTTPServer(("127.0.0.1", port), Preview)
    print("Preview: ready on port {} (press Ctrl+C to stop)".format(port), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if camera is not None:
            camera.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("speed", type=float)
    parser.add_argument("--camera-only", action="store_true")
    args = parser.parse_args()
    if not 0.05 <= args.speed <= 0.5:
        parser.error("speed must be between 0.05 and 0.5")

    if not args.camera_only:
        try:
            from jetbot import Robot
            test_motors(Robot.instance(), args.speed)
        except Exception as exc:
            print("Motor: FAILED: {}".format(exc), file=sys.stderr, flush=True)

    import cv2
    if not glob.glob("/dev/video*"):
        print("Camera: Linux has no /dev/video* device", flush=True)
        camera, sensor_id = None, None
    else:
        camera, sensor_id = find_camera(cv2)
    serve_preview(camera, sensor_id, cv2, 8765)


if __name__ == "__main__":
    main()
