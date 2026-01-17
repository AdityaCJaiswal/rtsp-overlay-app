# 🎥 StreamStudio - Real-Time RTSP Overlay Manager

StreamStudio is a low-latency, full-stack video overlay application designed for broadcast and monitoring environments. It allows users to overlay dynamic text and images onto live video feeds (RTSP or Webcam) with sub-200ms latency.

![StreamStudio Screenshot](./screenshot.png)

---

## 🚀 Key Features

- ⚡ **Ultra-Low Latency (<200ms)**: Custom-built MJPEG streaming pipeline (bypassing HLS buffering)
- 🛠 **Hybrid Video Engine**: Automatically switches between FFmpeg (for high-performance RTSP decoding) and OpenCV (for local webcam access)
- 🎨 **Dynamic Overlays**: Drag, drop, and resize text/image overlays in real-time
- 💾 **Persistence**: All overlay configurations are saved to MongoDB and restored on reload
- 🎛 **Professional UI**: Dark-mode interface with "Snap to Grid" precision tools
- 🛡 **Fault Tolerance**: Automatic connection recovery and fallback to webcam if RTSP stream fails

---

## 🏗 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React.js, `react-rnd` (Drag & Drop), `lucide-react` (Icons) |
| **Backend** | Python Flask, OpenCV (CV2), FFmpeg (Subprocess Pipe), Threading |
| **Database** | MongoDB (Containerized) |
| **DevOps** | Docker & Docker Compose |

---

## ⚙️ Architecture & Design Decisions

### 1. The "Audio vs. Latency" Trade-off

You will notice the volume control is present but **disabled**. This is intentional.

- **Decision**: I chose an MJPEG (Motion JPEG) stream over HLS/DASH
- **Reasoning**: Standard browser-based RTSP players (like HLS) introduce 10-15 seconds of latency. For an overlay tool, "drag-to-update" responsiveness is critical. MJPEG provides instant visual feedback (<200ms) at the cost of audio support
- **Future Work**: In production v2, I would implement WebRTC to support both low-latency video AND audio

### 2. The Hybrid Engine (FFmpeg + OpenCV)

The backend implements a smart factory pattern to select the best video driver:

- **RTSP URLs**: Spawns a dedicated FFmpeg process to handle UDP packet loss and prevent "smearing" artifacts
- **Webcam/Local**: Uses OpenCV for direct hardware access and driver compatibility

**Why both?**
- FFmpeg excels at network streams (buffer management, codec support)
- OpenCV provides simpler webcam integration without external dependencies

---

## 🏃‍♂️ How to Run

### Option A: The Easy Way (Docker) 🐳

**Prerequisite**: Docker Desktop must be running

1. Clone the repository:
```bash
   git clone https://github.com/yourusername/streamstudio.git
   cd streamstudio
```

2. Run the compose command:
```bash
   docker-compose up --build
```

3. Open [http://localhost:3000](http://localhost:3000)

4. **Note**: To use your local webcam inside Docker, you may need specific USB passthrough settings. For the best webcam demo experience, use **Option B**.

---

### Option B: Local Development (Recommended for Webcam Demos) 💻

**Prerequisites**: 
- Python 3.9+
- Node.js 16+
- MongoDB (running locally or via Docker)
- FFmpeg (optional, but recommended for RTSP streams)

#### Step 1: Start the Database
```bash
docker run -d -p 27017:27017 --name streamstudio-mongo mongo
```

Or, if you have MongoDB installed locally:
```bash
mongod --dbpath /path/to/data/db
```

#### Step 2: Start the Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Expected Output**:
```
🖥️  System Check: FFmpeg is ✅ INSTALLED
 * Running on http://127.0.0.1:5000
```

*(If FFmpeg is missing, you'll see "❌ MISSING (Using OpenCV Fallback)" - the app will still work, but RTSP performance will be degraded)*

#### Step 3: Start the Frontend
```bash
cd frontend
npm install
npm start
```

The app will automatically open at [http://localhost:3000](http://localhost:3000)

---

## 📁 Project Structure
```
streamstudio/
├── backend/
│   ├── app.py              # Flask server + video streaming engine
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   └── App.css         # Styling
│   ├── package.json        # Node dependencies
│   └── public/
├── docker-compose.yml      # Docker orchestration
├── Dockerfile.backend      # Backend container
├── Dockerfile.frontend     # Frontend container
└── README.md               # You are here!
```

---

## 🔌 API Documentation

### Video & Settings

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/video_feed` | Stream MJPEG video frames | N/A | `multipart/x-mixed-replace` stream |
| `GET` | `/settings` | Get current video source | N/A | `{"current_source": "0", "active_streams": 1}` |
| `POST` | `/settings` | Switch video source | `{"rtsp_url": "rtsp://..." or "0"}` | `{"message": "Source switched", "current_source": "..."}` |
| `POST` | `/test_connection` | Test RTSP connectivity | `{"rtsp_url": "rtsp://..."}` | `{"success": true, "message": "Connection OK"}` |

### Overlays (CRUD)

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/overlays` | Fetch all active overlays | N/A | `[{"_id": "...", "content": "Hello", "type": "text", ...}]` |
| `POST` | `/overlays` | Create a new overlay | `{"content": "Hello World", "type": "text", "x": 50, "y": 50, "width": 200, "height": 100}` | `{"_id": "64f3a...", ...}` |
| `PUT` | `/overlays/<id>` | Update overlay properties | `{"x": 100, "y": 150}` | `{"msg": "ok"}` |
| `DELETE` | `/overlays/<id>` | Remove an overlay | N/A | `{"msg": "ok"}` |

#### Example: Create Text Overlay
```bash
curl -X POST http://localhost:5000/overlays \
  -H "Content-Type: application/json" \
  -d '{
    "content": "LIVE",
    "type": "text",
    "x": 100,
    "y": 50,
    "width": 150,
    "height": 60
  }'
```

#### Example: Create Image Overlay
```bash
curl -X POST http://localhost:5000/overlays \
  -H "Content-Type: application/json" \
  -d '{
    "content": "https://example.com/logo.png",
    "type": "image",
    "x": 20,
    "y": 20,
    "width": 100,
    "height": 100
  }'
```

---

## 🧪 Testing & Usage Guide

### 1. Changing the Video Source

**Via UI** (Recommended):
1. Click "Change Source" in the sidebar
2. Enter one of the following:
   - `0` - Default webcam
   - `rtsp://192.168.1.100:554/stream` - Your IP camera
   - Leave empty and click "Apply" - Falls back to webcam
3. Click "Test Connection" to verify before applying
4. Click "Apply Source"

**Via Environment Variable**:
```bash
# In backend/.env
RTSP_URL=rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4
```

### 2. Connection Testing

The app includes a "Test Connection" button in the settings panel. It performs a quick handshake with the RTSP server to verify reachability **without breaking the active stream**.

### 3. Sample RTSP URLs

| Source | URL | Notes |
|--------|-----|-------|
| **Local Webcam** | `0` | Default, always works |
| **Big Buck Bunny (Public)** | `rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4` | May be unstable/slow |
| **Your IP Camera** | `rtsp://username:password@192.168.1.100:554/stream` | Replace with your credentials |

> ⚠️ **Note**: Public RTSP streams are often unreliable. For best results, use a local webcam or your own IP camera.

### 4. Creating Overlays

1. Enter text or image URL in the "Content" field
2. Select "Text Overlay" or "Image Overlay"
3. Click "Add Overlay"
4. Drag the overlay to reposition
5. Resize using the corner handles
6. Click the `×` button to delete

### 5. Snap to Grid

Enable "Snap to Grid" in the top bar for precise 10px alignment when positioning overlays.

---

## 🐛 Troubleshooting

### Issue: "FFmpeg is MISSING"

**Symptoms**: Backend logs show `❌ MISSING (Using OpenCV Fallback)`

**Solution**: Install FFmpeg
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

Then restart `python app.py`

---

### Issue: "Failed to load overlays"

**Symptoms**: Sidebar shows loading spinner indefinitely

**Solution**: Verify MongoDB is running
```bash
# Check if MongoDB container is running
docker ps | grep mongo

# Or check local MongoDB
mongo --eval "db.version()"
```

---

### Issue: "Stream shows black screen"

**Possible Causes**:
1. **RTSP URL is unreachable** → Click "Test Connection"
2. **Webcam is in use by another app** → Close Zoom/Skype/etc.
3. **Browser permissions** → Allow camera access when prompted

**Debug Steps**:
```bash
# Check backend logs
# You should see: "🚀 Starting FFmpeg Pipe..." or "📷 Starting Source: 0"

# Test RTSP manually
ffplay rtsp://your-url-here
```

---

### Issue: Video lags or skips frames

**Solution**: The app auto-scales to 720p. If still laggy:
1. Check your network bandwidth (RTSP requires stable connection)
2. Try reducing quality in `app.py`:
```python
   '-q:v', '8',  # Lower quality (was 5)
```

---

## 📦 Dependencies

### Backend (`requirements.txt`)
```txt
Flask==2.3.0
flask-cors==4.0.0
pymongo==4.5.0
opencv-python==4.8.0.76
numpy==1.24.3
```

### Frontend (`package.json`)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-rnd": "^10.4.1",
    "lucide-react": "^0.263.1"
  }
}
```

---

## 🔒 Known Limitations

1. **No Audio Support**: MJPEG streams are video-only. Audio would require WebRTC or HLS (with higher latency)
2. **Browser Compatibility**: Tested on Chrome/Edge. Firefox may have MJPEG rendering quirks
3. **Webcam in Docker**: Requires USB passthrough configuration (platform-dependent)
4. **Mobile Support**: Touch-based drag/resize is not optimized (desktop recommended)

---

## 🚀 Future Enhancements

- WebRTC integration for low-latency audio
- Multi-stream support (Picture-in-Picture)
- Overlay animation effects (fade in/out)
- Export overlay configurations as JSON
- User authentication & stream access control

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Aditya Jaiswal**  
Full Stack Engineer | High-Performance Video Systems  
📧 [adityacjaiswal@gmail.com](mailto:adityacjaiswal@gmail.com)  
🔗 [LinkedIn](https://www.linkedin.com/in/adityajaiswal1/) | [Portfolio](https://adityacjaiswal.github.io/)

---

## 🙏 Acknowledgments

- **FFmpeg** - The Swiss Army knife of video processing
- **React-RND** - Elegant drag-and-drop components
- **OpenCV** - Computer vision made accessible

---

## 📝 Assignment Submission

This project was built as part of the **RTSP Livestream Overlay Web Application** assignment.

**Submission Details**: 
- 🎥 Demo Video: [Link to video](https://youtu.be/XPwn3be6KI4)
- 💻 GitHub: [https://github.com/AdityaCJaiswal/rtsp-overlay-app](https://github.com/AdityaCJaiswal/rtsp-overlay-app)

---

**Built with ❤️ for real-time video applications**