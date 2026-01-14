import React, { useState, useEffect } from 'react';
import { Rnd } from 'react-rnd';
import { Play, Pause, Plus, Trash2, Grid3x3, Volume2, AlertCircle, Check, Video, Settings } from 'lucide-react';
import './App.css';

const API_URL = "http://localhost:5000";

// ============ OVERLAY COMPONENT ============
const Overlay = ({ data, onUpdate, onDelete, snapToGrid }) => {
  return (
    <Rnd
      size={{ width: data.width, height: data.height }}
      position={{ x: data.x, y: data.y }}
      bounds="parent"
      dragGrid={snapToGrid ? [10, 10] : undefined}
      resizeGrid={snapToGrid ? [10, 10] : undefined}
      onDragStop={(e, d) => {
        onUpdate(data._id, { x: d.x, y: d.y });
      }}
      onResizeStop={(e, direction, ref, delta, position) => {
        onUpdate(data._id, {
          width: parseInt(ref.style.width),
          height: parseInt(ref.style.height),
          ...position,
        });
      }}
      className="overlay-rnd"
    >
      <div className="overlay-content">
        {data.type === 'image' ? (
          <img 
            src={data.content} 
            alt="overlay" 
            className="overlay-image"
            draggable="false"
          />
        ) : (
          <p className="overlay-text">{data.content}</p>
        )}
        
        <button 
          className="overlay-delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(data._id);
          }}
        >
          ×
        </button>
      </div>
    </Rnd>
  );
};

// ============ NOTIFICATION COMPONENT ============
const Notification = ({ message, type, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="notification">
      {type === 'success' ? (
        <Check size={20} color="#10b981" />
      ) : (
        <AlertCircle size={20} color="#ef4444" />
      )}
      <span className="notification-text">{message}</span>
    </div>
  );
};

// ============ MAIN APP ============
function App() {
  const [overlays, setOverlays] = useState([]);
  const [newContent, setNewContent] = useState("");
  const [newType, setNewType] = useState("text");
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(50);
  const [snapToGrid, setSnapToGrid] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState(null);
  
  // Video source settings
  const [rtspUrl, setRtspUrl] = useState("");
  const [currentSource, setCurrentSource] = useState("Webcam");
  const [showSettings, setShowSettings] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);

  useEffect(() => {
    fetchOverlays();
    fetchCurrentSettings();
  }, []);

  const fetchOverlays = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/overlays`);
      const data = await res.json();
      setOverlays(data);
    } catch (err) {
      showNotification('Failed to load overlays', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/settings`);
      const data = await res.json();
      const source = data.current_source;
      setCurrentSource(source === 0 ? "Webcam" : source);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    }
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
  };

  const updateVideoSource = async () => {
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rtsp_url: rtspUrl })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        showNotification(data.message, 'success');
        setCurrentSource(data.current_source === 0 ? "Webcam" : data.current_source);
        setShowSettings(false);
        
        // Restart stream if currently playing
        if (isPlaying) {
          setIsPlaying(false);
          setTimeout(() => setIsPlaying(true), 500);
        }
      } else {
        showNotification(data.error || 'Failed to update source', 'error');
      }
    } catch (err) {
      showNotification('Failed to connect to backend', 'error');
    }
  };

  const testConnection = async () => {
    if (!rtspUrl.trim() && rtspUrl !== "0") {
      showNotification('Please enter a source URL or use "0" for webcam', 'error');
      return;
    }

    setTestingConnection(true);
    try {
      const res = await fetch(`${API_URL}/test_connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rtsp_url: rtspUrl })
      });
      
      const data = await res.json();
      
      if (data.success) {
        showNotification(`✓ ${data.message} ${data.resolution || ''}`, 'success');
      } else {
        showNotification(data.message, 'error');
      }
    } catch (err) {
      showNotification('Connection test failed', 'error');
    } finally {
      setTestingConnection(false);
    }
  };

  const addOverlay = async () => {
    if (!newContent.trim()) {
      showNotification('Please enter content', 'error');
      return;
    }
    try {
      await fetch(`${API_URL}/overlays`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: newContent,
          type: newType,
          x: 50, 
          y: 50, 
          width: 200, 
          height: 100
        })
      });
      setNewContent("");
      fetchOverlays();
      showNotification('Overlay added successfully', 'success');
    } catch (err) {
      showNotification('Failed to add overlay', 'error');
    }
  };

  const updateOverlay = async (id, newData) => {
    setOverlays(prev => prev.map(o => o._id === id ? { ...o, ...newData } : o));
    try {
      await fetch(`${API_URL}/overlays/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newData)
      });
    } catch (err) {
      showNotification('Failed to update overlay', 'error');
      fetchOverlays();
    }
  };

  const deleteOverlay = async (id) => {
    try {
      await fetch(`${API_URL}/overlays/${id}`, { method: 'DELETE' });
      setOverlays(prev => prev.filter(o => o._id !== id));
      showNotification('Overlay deleted', 'success');
    } catch (err) {
      showNotification('Failed to delete overlay', 'error');
    }
  };

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1 className="logo">
            <Play size={20} color="#3b82f6" />
            StreamStudio
          </h1>
          <p className="subtitle">Live Overlay Manager</p>
        </div>
        
        <div className="sidebar-content">
          {/* Video Source Section */}
          <div className="section">
            <h3 className="section-title">Video Source</h3>
            
            <div className="source-display">
              <Video size={16} color="#3b82f6" />
              <span className="source-text">
                {typeof currentSource === 'string' && currentSource.length > 30 
                  ? currentSource.substring(0, 30) + '...' 
                  : currentSource}
              </span>
            </div>
            
            <button 
              onClick={() => setShowSettings(!showSettings)} 
              className="btn-secondary"
            >
              <Settings size={18} />
              {showSettings ? 'Hide Settings' : 'Change Source'}
            </button>
            
            {showSettings && (
              <div className="settings-panel">
                <div className="input-group">
                  <label className="label">RTSP/HTTP URL or Device</label>
                  <input 
                    type="text" 
                    placeholder="rtsp://... or leave empty for webcam" 
                    value={rtspUrl} 
                    onChange={(e) => setRtspUrl(e.target.value)}
                    className="input"
                  />
                  <div className="input-hint">
                    Examples: rtsp://192.168.1.100:554/stream or "0" for default webcam
                  </div>
                </div>
                
                <div className="button-group">
                  <button 
                    onClick={testConnection}
                    disabled={testingConnection}
                    className="btn-test"
                  >
                    {testingConnection ? 'Testing...' : 'Test Connection'}
                  </button>
                  
                  <button 
                    onClick={updateVideoSource}
                    className="btn-primary"
                  >
                    Apply Source
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Add Overlay Section */}
          <div className="section">
            <h3 className="section-title">Add Overlay</h3>
            
            <div className="input-group">
              <label className="label">Content</label>
              <input 
                type="text" 
                placeholder="Text or Image URL" 
                value={newContent} 
                onChange={(e) => setNewContent(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addOverlay()}
                className="input"
              />
            </div>
            
            <div className="input-group">
              <label className="label">Type</label>
              <select 
                value={newType} 
                onChange={(e) => setNewType(e.target.value)} 
                className="select"
              >
                <option value="text">Text Overlay</option>
                <option value="image">Image Overlay</option>
              </select>
            </div>
            
            <button onClick={addOverlay} className="btn-primary">
              <Plus size={18} />
              Add Overlay
            </button>
          </div>

          {/* Active Overlays Section */}
          <div className="section">
            <h3 className="section-title">
              Active Overlays ({overlays.length})
            </h3>
            
            {loading ? (
              <div className="empty-state">Loading overlays...</div>
            ) : overlays.length === 0 ? (
              <div className="empty-state">
                No overlays yet. Add your first overlay above.
              </div>
            ) : (
              <div className="overlay-list">
                {overlays.map((overlay) => (
                  <div key={overlay._id} className="overlay-item">
                    <div className="overlay-icon">
                      {overlay.type === 'image' ? '🖼️' : 'T'}
                    </div>
                    <div className="overlay-info">
                      <div className="overlay-content-text">
                        {overlay.content.length > 20 
                          ? overlay.content.substring(0, 20) + '...' 
                          : overlay.content}
                      </div>
                      <div className="overlay-type">
                        {overlay.type} • {Math.round(overlay.width)}×{Math.round(overlay.height)}
                      </div>
                    </div>
                    <div className="overlay-actions">
                      <button 
                        className="icon-btn"
                        onClick={() => deleteOverlay(overlay._id)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        {/* TOP BAR */}
        <div className="top-bar">
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className={`play-btn ${isPlaying ? 'playing' : 'paused'}`}
          >
            {isPlaying ? <Pause size={20} /> : <Play size={20} />}
          </button>

          <div className="volume-control">
            <Volume2 size={18} color="#666" />
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={volume} 
              onChange={(e) => setVolume(e.target.value)}
              disabled={true}
              className="slider"
              title="Audio not supported - MJPEG streams are video-only"
            />
            <span className="volume-text">{volume}%</span>
          </div>

          <div className="toggle-group">
            <Grid3x3 size={18} color="#666" />
            <span className="toggle-label">Snap to Grid</span>
            <button 
              onClick={() => setSnapToGrid(!snapToGrid)}
              className={`toggle ${snapToGrid ? 'active' : ''}`}
            >
              <div className="toggle-knob" />
            </button>
          </div>
        </div>

        {/* VIDEO CONTAINER */}
        <div className="video-container">
          <div className="video-wrapper">
            {isPlaying ? (
              <img 
                src={`${API_URL}/video_feed?t=${Date.now()}`} 
                alt="Stream" 
                className="video-stream"
              />
            ) : (
              <div className="placeholder">
                <Play size={64} color="#333" />
                <h3>Stream Paused</h3>
                <p>Click play to start streaming</p>
              </div>
            )}

            {overlays.map((overlay) => (
              <Overlay 
                key={overlay._id} 
                data={overlay} 
                onUpdate={updateOverlay} 
                onDelete={deleteOverlay}
                snapToGrid={snapToGrid}
              />
            ))}
          </div>
        </div>
      </div>

      {/* NOTIFICATIONS */}
      {notification && (
        <Notification 
          message={notification.message} 
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}
    </div>
  );
}

export default App;