import React from 'react';
import { Rnd } from 'react-rnd';

const Overlay = ({ data, onUpdate, onDelete }) => {
  // data = { _id, x, y, width, height, content, type }

  return (
    <Rnd
      // 1. Set initial size and position from DB
      size={{ width: data.width, height: data.height }}
      position={{ x: data.x, y: data.y }}
      
      // 2. Constrain movement to the video player box
      bounds="parent"
      
      // 3. When the user STOPS dragging, save to DB
      onDragStop={(e, d) => {
        onUpdate(data._id, { x: d.x, y: d.y });
      }}
      
      // 4. When the user STOPS resizing, save to DB
      onResizeStop={(e, direction, ref, delta, position) => {
        onUpdate(data._id, {
          width: ref.style.width,
          height: ref.style.height,
          ...position,
        });
      }}
      
      // Styling to make it look like a draggable widget
      style={{
        border: '1px dashed yellow', // Visible border to see the overlay
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'move',
        background: 'rgba(0,0,0,0.3)', // Semi-transparent
        color: 'white',
        fontWeight: 'bold',
        overflow: 'hidden' // Prevent content spilling
      }}
    >
      {/* 5. Render Content based on Type */}
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        {data.type === 'image' ? (
          <img 
            src={data.content} 
            alt="overlay" 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
            draggable="false" // Prevent browser native drag
          />
        ) : (
          <p style={{ margin: 0, padding: 5, textAlign: 'center' }}>
            {data.content}
          </p>
        )}
        
        {/* Delete Button (Top Right) */}
        <button 
          onClick={(e) => {
            e.stopPropagation(); // Don't trigger drag
            onDelete(data._id);
          }}
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            background: 'red',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            fontSize: '10px',
            zIndex: 100
          }}
        >
          X
        </button>
      </div>
    </Rnd>
  );
};

export default Overlay;