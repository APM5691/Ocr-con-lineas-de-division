import { useRef, useEffect, useState } from 'react';
import { useLinesStore } from '../hooks/useLinesStore';
import { getBackendURL } from '../config';

function ImageCard({ filename }) {
  const canvasRef = useRef(null);
  const imgRef = useRef(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragLineIndex, setDragLineIndex] = useState(null);
  
  const imageLines = useLinesStore((state) => state.lines[filename]) || [];
  const { addLine, removeLine, updateLine, replicateLines } = useLinesStore();
  const imageUrl = getBackendURL(`/api/images/${filename}`);

useEffect(() => {
  if (!imgLoaded) return;
  drawLines();
}, [imageLines, imgLoaded]);

  const drawLines = () => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    canvas.width = img.width;
    canvas.height = img.height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#ff0000';
    ctx.lineWidth = 2;

    imageLines.forEach((x) => {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    });
  };

  const handleCanvasClick = (e) => {
    if (isDragging) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    
    addLine(filename, x);
  };

  const handleMouseDown = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    
    const clickedLineIndex = imageLines.findIndex(lineX => Math.abs(lineX - x) < 5);
    
    if (clickedLineIndex !== -1) {
      setIsDragging(true);
      setDragLineIndex(clickedLineIndex);
    }
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    
    updateLine(filename, dragLineIndex, x);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragLineIndex(null);
  };

  const handleRemoveLast = () => {
    removeLine(filename);
  };

  const handleReplicate = () => {
    const mode = window.confirm(
      '¿Replicar solo en imágenes vacías?\n\nOK = Solo vacías\nCancelar = Sobrescribir todas'
    );

    console.log(filename, mode);
    

    replicateLines(filename, mode);
  };

  return (
    <div className="image-card">
      <div className="image-wrapper">
        <img 
          ref={imgRef}
          src={imageUrl} 
          alt={filename}
          onLoad={() => setImgLoaded(true)}
        />
        <canvas
          ref={canvasRef}
          className="line-canvas"
          onClick={handleCanvasClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
      </div>
      <div className="card-footer">
        <span className="filename">{filename}</span>
        <span className="line-count">{imageLines.length} líneas</span>
        <div className="card-actions">
          <button 
            onClick={handleRemoveLast}
            disabled={imageLines.length === 0}
            className="btn-remove"
          >
            Eliminar última
          </button>
          <button 
            onClick={handleReplicate}
            disabled={imageLines.length === 0}
            className="btn-replicate"
          >
            Replicar a todas
          </button>
        </div>
      </div>
    </div>
  );
}

export default ImageCard;