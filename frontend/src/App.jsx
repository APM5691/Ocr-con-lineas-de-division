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
  const [processingStatus, setProcessingStatus] = useState(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const { lines, exportJSON, loadLines, setImages: setStoreImages } = useLinesStore();

  useEffect(() => {
    loadLastProject();
  }, []);

  const loadLastProject = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/projects');
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
    const response = await fetch(`http://localhost:5000/api/set-project/${projectName}`, {
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

  const handleProcessOCR = async () => {
    if (!projectName) {
      alert('No hay proyecto activo');
      return;
    }

    setProcessingStatus('pending');
    setProcessingProgress(0);

    try {
      // Paso 1: Iniciar procesamiento OCR
      console.log(`Iniciando OCR para proyecto: ${projectName}`);
      
      const processResponse = await fetch('http://localhost:8000/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project: projectName,
          json_filename: 'lines.json'
        })
      });

      if (!processResponse.ok) {
        throw new Error(`Error iniciando procesamiento: ${processResponse.statusText}`);
      }

      const processData = await processResponse.json();
      console.log('Procesamiento iniciado:', processData);
      
      setProcessingStatus('processing');
      setProcessingProgress(25);

      // Paso 2: Monitorear progreso cada 2 segundos
      let isComplete = false;
      let attempts = 0;
      const maxAttempts = 180; // 6 minutos máximo

      while (!isComplete && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000)); // Esperar 2 segundos
        attempts++;

        const statusResponse = await fetch(
          `http://localhost:8000/api/process-status/${projectName}`
        );

        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          console.log(`Progreso: ${statusData.progress}`);

          if (statusData.status === 'processing') {
            setProcessingProgress(50);
            setProcessingStatus(`processing: ${statusData.progress}`);
          } else if (statusData.status === 'completed') {
            setProcessingProgress(90);
            setProcessingStatus('completed');
            isComplete = true;

            // Paso 3: Descargar Excel
            console.log('Descargando Excel...');
            await downloadExcel(projectName);
            
            setProcessingProgress(100);
            setProcessingStatus('success');
            alert('✅ Procesamiento completado y Excel descargado');
            
            setTimeout(() => setProcessingStatus(null), 3000);
          } else if (statusData.status === 'error') {
            throw new Error(`Error en procesamiento: ${statusData.error_message}`);
          }
        }
      }

      if (!isComplete) {
        throw new Error('Timeout: Procesamiento tardó demasiado');
      }
    } catch (error) {
      console.error('Error en procesamiento OCR:', error);
      setProcessingStatus('error');
      alert(`❌ Error: ${error.message}`);
      setTimeout(() => setProcessingStatus(null), 5000);
    }
  };

  const downloadExcel = async (project) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/download-excel/${project}`
      );

      if (!response.ok) {
        throw new Error(`Error descargando Excel: ${response.statusText}`);
      }

      // Extraer nombre del archivo del header Content-Disposition si existe
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `${project}_resultado.xlsx`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Crear blob y descargar
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log(`✅ Excel descargado: ${filename}`);
    } catch (error) {
      console.error('Error descargando Excel:', error);
      throw error;
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
          
          {/* Barra de progreso de procesamiento */}
          {processingStatus && (
            <div className="processing-status">
              <div className="status-header">
                {processingStatus === 'success' ? (
                  <span className="status-label success">✅ Completado</span>
                ) : processingStatus === 'error' ? (
                  <span className="status-label error">❌ Error</span>
                ) : processingStatus === 'pending' ? (
                  <span className="status-label pending">⏳ Iniciando...</span>
                ) : (
                  <span className="status-label processing">⏸️ {processingStatus}</span>
                )}
              </div>
              <div className="progress-bar-container">
                <div 
                  className="progress-bar" 
                  style={{ width: `${processingProgress}%` }}
                ></div>
              </div>
              <div className="progress-text">{processingProgress}%</div>
            </div>
          )}

          <div className="controls">
            <button 
              onClick={handleExport} 
              className="btn-export"
              disabled={processingStatus !== null}
            >
              📥 Exportar JSON ({displayImages.length} imágenes)
            </button>
            
            <button 
              onClick={handleProcessOCR}
              className="btn-process"
              disabled={processingStatus !== null || displayImages.length === 0}
            >
              {processingStatus ? '⏳ Procesando...' : '🔄 Procesar OCR'}
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