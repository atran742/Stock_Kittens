import React, { useState, useRef } from 'react';
import './ImageUpload.css';

export default function ImageUpload() {
  const [preview, setPreview] = useState(null);
  const inputRef = useRef();

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setPreview(ev.target.result);
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setPreview(ev.target.result);
    reader.readAsDataURL(file);
  };

  return (
    <div
      className="upload-area"
      onClick={() => inputRef.current.click()}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*,.gif"
        onChange={handleFile}
        style={{ display: 'none' }}
      />
      {preview ? (
        <div className="preview-wrap">
          <img src={preview} alt="Your kitten" className="preview-img" />
          <div className="preview-label">Looking cute! 😻 Click to change</div>
        </div>
      ) : (
        <>
          <div className="upload-cat">🐱</div>
          <div className="upload-label">Drop your kitten here!</div>
          <div className="upload-sub">Upload a GIF or image to customize your dashboard</div>
        </>
      )}
    </div>
  );
}
