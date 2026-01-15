import cv2
import time
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import threading

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/rtsp_db")
client = MongoClient(MONGO_URI)
db = client.get_database("rtsp_db")
overlays_collection = db.get_collection("overlays")

# Global Video Source State
app_config = {
    "source": 0,
    "active_streams": 0,
    "lock": threading.Lock()
}

# --- VIDEO PIPELINE ---
def generate_frames():
    """Generate video frames from the current source"""
    with app_config["lock"]:
        current_source = app_config["source"]
        app_config["active_streams"] += 1
    
    print(f"📷 Starting Stream from source: {current_source}")
    
    # Initialize camera with timeout
    camera = cv2.VideoCapture(current_source)
    
    # Set timeout for network streams
    if isinstance(current_source, str):
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not camera.isOpened():
        print(f"❌ Error: Could not open video source: {current_source}")
        # Return error frame
        error_frame = create_error_frame("Failed to connect to video source")
        ret, buffer = cv2.imencode('.jpg', error_frame)
        frame_bytes = buffer.tobytes()
        
        with app_config["lock"]:
            app_config["active_streams"] -= 1
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        return

    try:
        while True:
            success, frame = camera.read()
            
            if not success:
                print("⚠️ Failed to read frame, attempting to reconnect...")
                # Try to reconnect for streams
                if isinstance(current_source, str):
                    camera.release()
                    time.sleep(1)
                    camera = cv2.VideoCapture(current_source)
                    if not camera.isOpened():
                        break
                else:
                    # For file/webcam, loop back
                    camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    except GeneratorExit:
        print("🔌 Client disconnected")
    except Exception as e:
        print(f"❌ Stream error: {e}")
    finally:
        camera.release()
        with app_config["lock"]:
            app_config["active_streams"] -= 1
        print(f"🛑 Stream stopped. Active streams: {app_config['active_streams']}")

def create_error_frame(message):
    """Create a black frame with error message"""
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, message, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, (255, 255, 255), 2)
    return frame

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

# --- SETTINGS API ---
@app.route('/settings', methods=['GET'])
def get_settings():
    """Get current video source settings"""
    return jsonify({
        "current_source": app_config["source"],
        "active_streams": app_config["active_streams"]
    })

@app.route('/settings', methods=['POST'])
def update_settings():
    """Update video source settings"""
    data = request.json
    new_source = data.get('rtsp_url', '').strip()
    
    # Determine source type
    if not new_source or new_source == "0" or new_source.lower() == "webcam":
        app_config["source"] = 0  # Webcam
        msg = "Switched to Webcam (Device 0)"
        source_type = "webcam"
    else:
        # Validate RTSP/HTTP URL
        if new_source.startswith(('rtsp://', 'http://', 'https://')):
            app_config["source"] = new_source
            msg = f"Switched to stream: {new_source}"
            source_type = "stream"
        else:
            # Try to interpret as device index
            try:
                device_index = int(new_source)
                app_config["source"] = device_index
                msg = f"Switched to Webcam (Device {device_index})"
                source_type = "webcam"
            except ValueError:
                return jsonify({
                    "error": "Invalid source. Use webcam (0) or valid RTSP/HTTP URL"
                }), 400
    
    print(f"⚙️ Settings Updated: {msg}")
    
    return jsonify({
        "message": msg,
        "current_source": app_config["source"],
        "source_type": source_type,
        "active_streams": app_config["active_streams"]
    })

@app.route('/test_connection', methods=['POST'])
def test_connection():
    """Test if a video source is accessible"""
    data = request.json
    test_source = data.get('rtsp_url', '').strip()
    
    if not test_source or test_source == "0":
        test_source = 0
    
    print(f"🔍 Testing connection to: {test_source}")
    
    try:
        cap = cv2.VideoCapture(test_source)
        
        if not cap.isOpened():
            return jsonify({
                "success": False,
                "message": "Failed to connect to source"
            }), 400
        
        # Try to read a frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return jsonify({
                "success": False,
                "message": "Connected but failed to read frame"
            }), 400
        
        return jsonify({
            "success": True,
            "message": "Connection successful!",
            "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

# --- CRUD API ENDPOINTS ---
@app.route('/overlays', methods=['GET'])
def get_overlays():
    """Get all overlays"""
    overlays = []
    for doc in overlays_collection.find():
        doc['_id'] = str(doc['_id'])
        overlays.append(doc)
    return jsonify(overlays)

@app.route('/overlays', methods=['POST'])
def create_overlay():
    """Create a new overlay"""
    data = request.json
    if not data: 
        return jsonify({"error": "No data provided"}), 400
    
    new_overlay = {
        "type": data.get("type", "text"),
        "content": data.get("content", "New Overlay"),
        "x": data.get("x", 50),
        "y": data.get("y", 50),
        "width": data.get("width", 200),
        "height": data.get("height", 100)
    }
    
    result = overlays_collection.insert_one(new_overlay)
    new_overlay['_id'] = str(result.inserted_id)
    return jsonify(new_overlay), 201

@app.route('/overlays/<id>', methods=['PUT'])
def update_overlay(id):
    """Update an existing overlay"""
    try:
        result = overlays_collection.update_one(
            {"_id": ObjectId(id)}, 
            {"$set": request.json}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Overlay not found"}), 404
        return jsonify({"message": "Updated successfully"})
    except Exception as e: 
        return jsonify({"error": str(e)}), 400

@app.route('/overlays/<id>', methods=['DELETE'])
def delete_overlay(id):
    """Delete an overlay"""
    try:
        result = overlays_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Overlay not found"}), 404
        return jsonify({"message": "Deleted successfully"})
    except Exception as e: 
        return jsonify({"error": str(e)}), 400

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "status": "Backend running",
        "current_source": app_config["source"],
        "active_streams": app_config["active_streams"]
    })

if __name__ == '__main__':
    print("🚀 StreamStudio Backend Starting...")
    print(f"📡 Default source: {app_config['source']}")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)