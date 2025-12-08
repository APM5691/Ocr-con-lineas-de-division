import { useState, useEffect } from 'react';
import Uploader from './components/Uploader';
import ImageGrid from './components/ImageGrid';
import FilterControls from './components/FilterControls';
import { useLinesStore } from './hooks/useLinesStore';
import { getBackendURL, getPaddleURL } from './config';
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
    let isMounted = true;
    
    const load = async () => {
      try {
        console.log('Intentando cargar último proyecto desde', getBackendURL('/api/projects'));
        
        const response = await fetch(getBackendURL('/api/projects'));
        
        if (!response.ok) {
          console.error('Error en respuesta:', response.status, response.statusText);
          if (isMounted) setLoading(false);
          return;
        }
        
        const data = await response.json();
        console.log('Proyectos obtenidos:', data);
        
        if (!isMounted) return;
        
        if (data.projects && data.projects.length > 0) {
          const lastProject = data.projects[0]; // El primero está ordenado por más reciente
          console.log('Cargando proyecto:', lastProject.name);

          await loadProject(lastProject.name);
        } else {
          console.log('No hay proyectos disponibles');
          setLoading(false);
        }
      } catch (error) {
        console.error('Error cargando proyecto:', error);
        if (isMounted) setLoading(false);
      }
    };
    
    load();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const loadProject = async (projectName) => {
    try {
      console.log(`Estableciendo proyecto activo: ${projectName}`);
      
      const response = await fetch(getBackendURL(`/api/set-project/${projectName}`), {
        method: 'POST'
      });
      
      if (!response.ok) {
        console.error('Error al establecer proyecto:', response.status, response.statusText);
        setLoading(false);
        return;
      }
      
      const data = await response.json();
      console.log('Proyecto cargado:', data);
      console.log('Imágenes recibidas:', data.images);
      
      const projectImages = data.images || [];
      setImages(projectImages);
      setFilteredImages(projectImages);
      setProjectName(data.project);
      setStoreImages(projectImages);
      
      // Las líneas pueden venir en dos formatos:
      // 1. Si es un JSON exportado: { lines: {...}, line_gap: 6.5, exported_at: "...", total_lines: N }
      // 2. Si es un objeto simple: { img_001.jpg: [10, 20], ... }
      const projectLines = data.lines || {};
      const linesToLoad = projectLines.lines || projectLines;

      console.log('Datos cargados:', { projectImages, projectLines, linesToLoad });

      loadLines(linesToLoad);
      
      setLoading(false);
      console.log(`✓ Proyecto '${data.project}' cargado con ${projectImages.length} imágenes y ${Object.keys(linesToLoad).length} imágenes con líneas`);
    } catch (error) {
      console.error('Error cargando proyecto:', error);
      setLoading(false);
    }
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
    if (!projectName) {
      alert('No hay proyecto activo');
      return;
    }

    try {
      const response = await fetch(getBackendURL('/api/export-lines'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lines: lines,
          line_gap: 6.5
        })
      });

      if (!response.ok) {
        throw new Error(`Error exportando: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Líneas exportadas:', data);
      alert(`✅ Líneas exportadas correctamente\nTotal: ${data.total_lines} líneas`);
    } catch (error) {
      console.error('Error al exportar:', error);
      alert(`❌ Error exportando líneas: ${error.message}`);
    }
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
      
      const processResponse = await fetch(getPaddleURL('/api/process'), {
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
          getPaddleURL(`/api/process-status/${projectName}`)
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
        getPaddleURL(`/api/download-excel/${project}`)
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
            <h2>Cargando últimos proyectos...</h2>
            <p>Conectando a http://localhost:5000/api/projects</p>
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