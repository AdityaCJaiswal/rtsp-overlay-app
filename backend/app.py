import cv2
import time
import threading
import subprocess
import shutil
import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import atexit

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/rtsp_db")
client = MongoClient(MONGO_URI)
db = client.get_database("rtsp_db")
overlays_collection = db.get_collection("overlays")

# Check for FFmpeg availability
FFMPEG_PATH = shutil.which('ffmpeg')
HAS_FFMPEG = FFMPEG_PATH is not None

print(f"🖥️  System Check: FFmpeg is {'✅ INSTALLED' if HAS_FFMPEG else '❌ MISSING (Using OpenCV Fallback)'}")

# Global State
app_config = {
    "source": 0,            # Current Source (0 or RTSP URL)
    "camera_thread": None,  # The active background worker
    "lock": threading.Lock()
}

# ==========================================
# ENGINE 1: FFMPEG (High Performance RTSP)
# ==========================================
class FFmpegCamera:
    def __init__(self, src):
        self.src = src
        self.stopped = False
        self.frame = None
        self.status = False
        
        # FFmpeg Command:
        # -rtsp_transport tcp: Prevent gray/green smear artifacts
        # -i src: Input
        # -f image2pipe: Output stream of images
        # -vcodec mjpeg: Encode as JPEG
        # -s 1280x720: Resize to 720p (Massive speed boost vs 1080p)
        # -q:v 5: Quality (Balance size/quality)
        cmd = [
            FFMPEG_PATH,
            '-loglevel', 'error',
            '-rtsp_transport', 'tcp',
            '-i', src,
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            '-s', '1280x720',
            '-q:v', '5',
            '-'
        ]
        
        print(f"🚀 Starting FFmpeg Pipe: {' '.join(cmd)}")
        self.process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=10**7
        )
        
        # Start background reader thread
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        """Reads raw bytes from FFmpeg stdout and parses JPEGs"""
        buffer = b""
        chunk_size = 4096
        
        while not self.stopped:
            # Read chunk
            chunk = self.process.stdout.read(chunk_size)
            if not chunk:
                self.status = False
                break
            
            buffer += chunk
            
            # Look for JPEG Start (0xFFD8) and End (0xFFD9)
            a = buffer.find(b'\xff\xd8')
            b = buffer.find(b'\xff\xd9')
            
            if a != -1 and b != -1:
                # FIX: Ensure End is after Start to avoid corruption
                if b > a:
                    jpg = buffer[a:b+2]
                    buffer = buffer[b+2:] # Keep remaining bytes for next frame
                    self.frame = jpg
                    self.status = True
                else:
                    # Garbage data (End byte appeared before Start), discard it
                    buffer = buffer[b+2:]
                    
            elif len(buffer) > 10**7:
                 # Safety: Clear buffer if no frame found (prevent memory leak)
                 buffer = b""

    def get_frame(self):
        return self.frame

    def stop(self):
        self.stopped = True
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except:
                self.process.kill()

# ==========================================
# ENGINE 2: OPENCV (Reliable Fallback / Webcam)
# ==========================================
class OpenCVCamera:
    def __init__(self, src=0):
        self.src = src
        
        # Force TCP if it's an RTSP stream (OpenCV backend)
        if isinstance(src, str) and src.startswith("rtsp"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            
        self.capture = cv2.VideoCapture(src)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.status, self.frame = self.capture.read()
        self.stopped = False
        
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while not self.stopped:
            if self.capture.isOpened():
                # Grab to clear buffer
                self.capture.grab()
                status, frame = self.capture.retrieve()
                if status:
                    self.frame = frame
                    self.status = True
                else:
                    self.status = False
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

    def get_frame(self):
        if not self.status or self.frame is None:
            return None
        
        # Resize to 720p (Performance optimization)
        h, w = self.frame.shape[:2]
        if h > 720:
            aspect_ratio = w / h
            new_w = int(720 * aspect_ratio)
            resized = cv2.resize(self.frame, (new_w, 720), interpolation=cv2.INTER_AREA)
        else:
            resized = self.frame
            
        ret, jpeg = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return jpeg.tobytes()

    def stop(self):
        self.stopped = True
        if self.capture.isOpened():
            self.capture.release()

# --- STREAM GENERATOR ---
def generate_frames():
    # Initialize the camera thread if needed
    if app_config["camera_thread"] is None:
        src = app_config["source"]
        
        # LOGIC: Choose Engine
        use_ffmpeg = False
        if HAS_FFMPEG and isinstance(src, str) and src.startswith("rtsp"):
            use_ffmpeg = True
            
        print(f"📷 Starting Source: {src} | Engine: {'FFMPEG' if use_ffmpeg else 'OPENCV'}")
        
        if use_ffmpeg:
            app_config["camera_thread"] = FFmpegCamera(src)
        else:
            app_config["camera_thread"] = OpenCVCamera(src)
            
        time.sleep(1) # Warmup

    camera = app_config["camera_thread"]

    while True:
        frame_bytes = camera.get_frame()
        
        if frame_bytes is None:
            time.sleep(0.1)
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.03) # Cap at ~30 FPS

# --- ROUTES ---

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/settings', methods=['GET'])
def get_settings():
    return jsonify({
        "current_source": app_config["source"],
        "active_streams": 1 if app_config["camera_thread"] else 0
    })

@app.route('/settings', methods=['POST'])
def update_settings():
    data = request.json
    new_source = data.get('rtsp_url', '').strip()
    
    # Determine new source
    target = 0
    if new_source and new_source != "0":
        target = new_source

    # Stop old thread
    if app_config["camera_thread"]:
        app_config["camera_thread"].stop()
        app_config["camera_thread"] = None
    
    # Update state (Generator will restart thread on next request)
    app_config["source"] = target
    
    return jsonify({"message": f"Source switched to {target}", "current_source": target})

@app.route('/test_connection', methods=['POST'])
def test_connection():
    # Quick connectivity check using OpenCV (FFmpeg is too heavy for a quick test)
    data = request.json
    src = data.get('rtsp_url', 0)
    if src == "0": src = 0
    
    cap = cv2.VideoCapture(src)
    if cap.isOpened():
        ret, _ = cap.read()
        cap.release()
        if ret: return jsonify({"success": True, "message": "Connection OK"})
    return jsonify({"success": False, "message": "Connection Failed"})

# --- CRUD (UNCHANGED) ---
@app.route('/overlays', methods=['GET'])
def get_overlays():
    overlays = []
    for doc in overlays_collection.find():
        doc['_id'] = str(doc['_id'])
        overlays.append(doc)
    return jsonify(overlays)

@app.route('/overlays', methods=['POST'])
def create_overlay():
    data = request.json
    res = overlays_collection.insert_one(data)
    data['_id'] = str(res.inserted_id)
    return jsonify(data), 201

@app.route('/overlays/<id>', methods=['PUT'])
def update_overlay(id):
    overlays_collection.update_one({"_id": ObjectId(id)}, {"$set": request.json})
    return jsonify({"msg": "ok"})

@app.route('/overlays/<id>', methods=['DELETE'])
def delete_overlay(id):
    overlays_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"msg": "ok"})

# Cleanup
def cleanup():
    if app_config["camera_thread"]:
        app_config["camera_thread"].stop()
atexit.register(cleanup)

if __name__ == '__main__':
    # host='0.0.0.0' exposes the server to the Docker network
    app.run(host='0.0.0.0', debug=True, port=5000, threaded=True)