import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const ROISelector = ({ imageUrl, onSave, initialROIs = [] }) => {
  const canvasRef = useRef(null);
  const [image, setImage] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState(null);
  const [rois, setRois] = useState(initialROIs);
  const [currentROIType, setCurrentROIType] = useState('code');
  const [scale, setScale] = useState(1);

  const roiColors = {
    code: { stroke: '#3b82f6', fill: 'rgba(59, 130, 246, 0.2)', label: 'Code ROI' },
    keyword: { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.2)', label: 'Keyword ROI' },
    child_marker: { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.2)', label: 'Child Marker ROI' }
  };

  useEffect(() => {
    if (imageUrl) {
      const img = new Image();
      img.onload = () => {
        setImage(img);
        drawCanvas(img, rois);
      };
      img.src = imageUrl;
    }
  }, [imageUrl]);

  useEffect(() => {
    if (image) {
      drawCanvas(image, rois);
    }
  }, [rois, image]);

  const drawCanvas = (img, currentRois) => {
    const canvas = canvasRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    
    // Calculer l'échelle pour adapter l'image
    const maxWidth = 800;
    const maxHeight = 600;
    let newScale = Math.min(maxWidth / img.width, maxHeight / img.height, 1);
    setScale(newScale);

    canvas.width = img.width * newScale;
    canvas.height = img.height * newScale;

    // Dessiner l'image
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    // Dessiner les ROIs existants
    currentRois.forEach(roi => {
      const color = roiColors[roi.type] || roiColors.code;
      ctx.strokeStyle = color.stroke;
      ctx.fillStyle = color.fill;
      ctx.lineWidth = 2;

      const x = roi.x * newScale;
      const y = roi.y * newScale;
      const w = roi.width * newScale;
      const h = roi.height * newScale;

      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);

      // Label
      ctx.fillStyle = color.stroke;
      ctx.font = 'bold 14px Arial';
      ctx.fillText(color.label, x + 5, y + 20);
    });
  };

  const handleMouseDown = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    setIsDrawing(true);
    setStartPos({ x, y });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing || !image) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const currentX = (e.clientX - rect.left) / scale;
    const currentY = (e.clientY - rect.top) / scale;

    // Redessiner
    drawCanvas(image, rois);

    // Dessiner le rectangle en cours
    const ctx = canvas.getContext('2d');
    const color = roiColors[currentROIType];
    ctx.strokeStyle = color.stroke;
    ctx.fillStyle = color.fill;
    ctx.lineWidth = 2;

    const width = currentX - startPos.x;
    const height = currentY - startPos.y;

    ctx.fillRect(startPos.x * scale, startPos.y * scale, width * scale, height * scale);
    ctx.strokeRect(startPos.x * scale, startPos.y * scale, width * scale, height * scale);
  };

  const handleMouseUp = (e) => {
    if (!isDrawing) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const endX = (e.clientX - rect.left) / scale;
    const endY = (e.clientY - rect.top) / scale;

    const width = Math.abs(endX - startPos.x);
    const height = Math.abs(endY - startPos.y);
    const x = Math.min(startPos.x, endX);
    const y = Math.min(startPos.y, endY);

    if (width > 10 && height > 10) {
      // Vérifier si ce type existe déjà
      const existingIndex = rois.findIndex(r => r.type === currentROIType);
      
      const newROI = {
        type: currentROIType,
        x: Math.round(x),
        y: Math.round(y),
        width: Math.round(width),
        height: Math.round(height)
      };

      if (existingIndex >= 0) {
        // Remplacer
        const newRois = [...rois];
        newRois[existingIndex] = newROI;
        setRois(newRois);
      } else {
        // Ajouter
        setRois([...rois, newROI]);
      }
    }

    setIsDrawing(false);
    setStartPos(null);
  };

  const handleDelete = (type) => {
    setRois(rois.filter(roi => roi.type !== type));
  };

  const handleSave = () => {
    onSave(rois);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 mb-4">
        <Label className="text-slate-200">Sélectionner le type de ROI:</Label>
        <Select value={currentROIType} onValueChange={setCurrentROIType}>
          <SelectTrigger className="w-64 bg-slate-800 border-slate-600 text-slate-100">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="code">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded" style={{backgroundColor: roiColors.code.stroke}}></span>
                Code ROI
              </span>
            </SelectItem>
            <SelectItem value="keyword">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded" style={{backgroundColor: roiColors.keyword.stroke}}></span>
                Keyword ROI
              </span>
            </SelectItem>
            <SelectItem value="child_marker">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded" style={{backgroundColor: roiColors.child_marker.stroke}}></span>
                Child Marker ROI (1/3, 2/3...)
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="bg-slate-800 rounded-lg p-4">
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className="cursor-crosshair border-2 border-slate-600 rounded"
        />
      </div>

      <div className="space-y-2">
        <Label className="text-slate-200">ROIs définies:</Label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {Object.entries(roiColors).map(([type, config]) => {
            const roi = rois.find(r => r.type === type);
            return (
              <div key={type} className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold" style={{color: config.stroke}}>
                    {config.label}
                  </span>
                  {roi && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(type)}
                      className="text-red-400 hover:text-red-300 h-6 px-2"
                    >
                      ✕
                    </Button>
                  )}
                </div>
                {roi ? (
                  <div className="text-xs text-slate-400 space-y-1">
                    <div>X: {roi.x}px, Y: {roi.y}px</div>
                    <div>W: {roi.width}px, H: {roi.height}px</div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500">Non défini</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          onClick={handleSave}
          className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-bold"
        >
          Sauvegarder les ROIs
        </Button>
        <Button
          onClick={() => setRois([])}
          variant="outline"
          className="border-slate-600 text-slate-300 hover:bg-slate-800"
        >
          Effacer tout
        </Button>
      </div>

      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
        <p className="text-sm text-blue-300">
          💡 <strong>Astuce:</strong> Dessinez les zones en cliquant et en faisant glisser sur l'image. 
          Vous pouvez définir une zone par type.
        </p>
      </div>
    </div>
  );
};

export default ROISelector;
