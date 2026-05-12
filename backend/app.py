from flask import Flask, Response, jsonify
from flask_cors import CORS
import cv2
import threading
import time
import numpy as np

from inference_service import SignRecognizer

app = Flask(__name__)
CORS(app)

recognizer = None
running = False
latest_status = {"prediction": "Camera inactive", "confidence": 0.0, "hand": "None"}
lock = threading.Lock()


@app.get("/")
def home():
    return jsonify({
        "message": "✅ Backend running",
        "routes": ["/start", "/stop", "/status", "/video_feed"]
    })


def create_inactive_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "Camera Inactive", (180, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
    cv2.putText(frame, "Press START in UI", (170, 270),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
    return frame


def encode_frame(frame):
    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        return b""
    frame_bytes = buffer.tobytes()
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
    )


def generate_frames():
    global recognizer, running, latest_status

    while True:
        with lock:
            is_running = running
            local_recognizer = recognizer

        if not is_running or local_recognizer is None:
            frame = create_inactive_frame()
            yield encode_frame(frame)
            time.sleep(0.1)
            continue

        frame, status = local_recognizer.read_frame()

        if frame is None:
            frame = create_inactive_frame()

        with lock:
            latest_status = status

        yield encode_frame(frame)


@app.get("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/status")
def status():
    with lock:
        return jsonify(latest_status)


@app.post("/start")
def start():
    global recognizer, running, latest_status
    with lock:
        if not running:
            recognizer = SignRecognizer(cam_index=0)
            running = True
            latest_status = {"prediction": "Starting...", "confidence": 0.0, "hand": "None"}
    return jsonify({"ok": True, "running": running})


@app.post("/stop")
def stop():
    global recognizer, running, latest_status
    with lock:
        running = False
        latest_status = {"prediction": "Camera inactive", "confidence": 0.0, "hand": "None"}

        if recognizer is not None:
            recognizer.release()
            recognizer = None

    return jsonify({"ok": True, "running": running})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
