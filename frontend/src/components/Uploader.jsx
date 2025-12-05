import { useState } from 'react';

function Uploader({ onSuccess }) {
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        onSuccess(data);
      } else {
        alert('Error al procesar PDF');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error de conexión con el servidor');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="uploader">
      <div className="upload-box">
        <h2>Sube tu PDF</h2>
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={uploading}
          id="file-input"
        />
        <label htmlFor="file-input" className="upload-label">
          {uploading ? 'Procesando...' : 'Seleccionar PDF'}
        </label>
      </div>
    </div>
  );
}

export default Uploader;