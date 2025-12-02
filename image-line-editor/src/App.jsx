import { useState, useEffect } from 'react';
import Uploader from './components/Uploader';
import ImageGrid from './components/ImageGrid';
import FilterControls from './components/FilterControls';
import { useLinesStore } from './hooks/useLinesStore';
import './App.css';

function App() {
  const [images, setImages] = useState([]);
  const [filteredImages, setFilteredImages] = useState([]);
  const [projectName, setProjectName] = useState('');
  const [loading, setLoading] = useState(true);
  const [filterActive, setFilterActive] = useState(false);
  const { lines, exportJSON, loadLines, setImages: setStoreImages } = useLinesStore();

  useEffect(() => {
    loadLastProject();
  }, []);

  const loadLastProject = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/projects');
      const data = await response.json();
      
      if (data.projects.length > 0) {
        const lastProject = data.projects[data.projects.length - 1];
        await loadProject(lastProject);
      }
    } catch (error) {
      console.error('Error cargando proyecto:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadProject = async (projectName) => {
    const response = await fetch(`http://localhost:8000/api/set-project/${projectName}`, {
      method: 'POST'
    });
    const data = await response.json();
    
    setImages(data.images);
    setFilteredImages(data.images);
    setProjectName(data.project);
    setStoreImages(data.images);
    loadLines(data.lines);
  };

  const handleUploadSuccess = (data) => {
    setImages(data.images);
    setFilteredImages(data.images);
    setProjectName(data.project);
    setStoreImages(data.images);
    loadLines({});
  };

  const handleFilter = (filtered) => {
    setFilteredImages(filtered);
    setStoreImages(filtered);
    setFilterActive(filtered.length !== images.length);
  };

  const handleClearFilters = () => {
    setFilteredImages(images);
    setStoreImages(images);
    setFilterActive(false);
  };

  const handleExport = async () => {
    const exportData = {};
    const imagesToExport = filteredImages;
    
    imagesToExport.forEach(img => {
      if (lines[img]) {
        exportData[img] = lines[img];
      }
    });

    try {
      const response = await fetch('http://localhost:8000/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lines: exportData })
      });
      
      if (response.ok) {
        alert(`JSON exportado: ${imagesToExport.length} imágenes`);
      }
    } catch (error) {
      console.error('Error al exportar:', error);
      alert('Error al exportar JSON');
    }
  };

  const displayImages = filteredImages;

  return (
    <div className="app">
      <header className="header">
        <h1>Editor de Líneas en Imágenes</h1>
        {projectName && <span className="project-name">Proyecto: {projectName}</span>}
      </header>

      {loading ? (
        <div className="uploader">
          <div className="upload-box">
            <h2>Cargando...</h2>
          </div>
        </div>
      ) : images.length === 0 ? (
        <Uploader onSuccess={handleUploadSuccess} />
      ) : (
        <div className="main-content">
          <FilterControls 
            allImages={images}
            onFilter={handleFilter}
            onClear={handleClearFilters}
            filterActive={filterActive}
          />
          <div className="controls">
            <button onClick={handleExport} className="btn-export">
              Exportar JSON ({displayImages.length} imágenes)
            </button>
            <span className="image-count">
              Mostrando {displayImages.length} de {images.length} imágenes
            </span>
          </div>
          <ImageGrid images={displayImages} />
        </div>
      )}
    </div>
  );
}

export default App;