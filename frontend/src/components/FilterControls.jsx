import { useState } from 'react';

function FilterControls({ allImages, onFilter, onClear, filterActive }) {
  const [searchValue, setSearchValue] = useState('');
  const [rangeFrom, setRangeFrom] = useState('');
  const [rangeTo, setRangeTo] = useState('');
  const [activeFilter, setActiveFilter] = useState(null); // 'search' | 'range' | null

  const normalizeImageName = (input) => {
    if (input.startsWith('img_') && input.endsWith('.jpg')) {
      return input;
    }
    const num = parseInt(input);
    if (!isNaN(num)) {
      return `img_${String(num).padStart(3, '0')}.jpg`;
    }
    return input;
  };

  const handleSearch = () => {
    if (!searchValue.trim()) {
      alert('Ingresa un número o nombre de imagen');
      return;
    }

    if (activeFilter === 'range') {
      const confirm = window.confirm('Ya hay un rango activo. ¿Desactivarlo y buscar?');
      if (!confirm) return;
      setRangeFrom('');
      setRangeTo('');
    }

    const targetImage = normalizeImageName(searchValue.trim());
    const found = allImages.find(img => img === targetImage);

    if (found) {
      onFilter([found]);
      setActiveFilter('search');
    } else {
      alert(`No se encontró la imagen: ${targetImage}`);
    }
  };

  const handleRangeFilter = () => {
    if (!rangeFrom.trim() || !rangeTo.trim()) {
      alert('Ingresa ambos valores del rango');
      return;
    }

    if (activeFilter === 'search') {
      const confirm = window.confirm('Ya hay una búsqueda activa. ¿Desactivarla y aplicar rango?');
      if (!confirm) return;
      setSearchValue('');
    }

    const fromNum = parseInt(rangeFrom);
    const toNum = parseInt(rangeTo);

    if (isNaN(fromNum) || isNaN(toNum)) {
      alert('Ingresa números válidos');
      return;
    }

    if (fromNum > toNum) {
      alert('El rango inicial debe ser menor al final');
      return;
    }

    const filtered = allImages.filter(img => {
      const match = img.match(/img_(\d+)\.jpg/);
      if (match) {
        const num = parseInt(match[1]);
        return num >= fromNum && num <= toNum;
      }
      return false;
    });

    if (filtered.length === 0) {
      alert(`No se encontraron imágenes en el rango ${fromNum}-${toNum}`);
      return;
    }

    onFilter(filtered);
    setActiveFilter('range');
  };

  const handleClear = () => {
    if (!filterActive) return;
    
    const confirm = window.confirm('¿Limpiar filtros y mostrar todas las imágenes?');
    if (!confirm) return;

    setSearchValue('');
    setRangeFrom('');
    setRangeTo('');
    setActiveFilter(null);
    onClear();
  };

  return (
    <div className="filter-controls">
      <div className="filter-group">
        <label>Buscar imagen:</label>
        <input
          type="text"
          placeholder="5, 005, img_005.jpg"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          disabled={activeFilter === 'range'}
        />
        <button onClick={handleSearch} disabled={activeFilter === 'range'}>
          Buscar
        </button>
      </div>

      <div className="filter-group">
        <label>Rango:</label>
        <input
          type="number"
          placeholder="Desde"
          value={rangeFrom}
          onChange={(e) => setRangeFrom(e.target.value)}
          disabled={activeFilter === 'search'}
        />
        <span>hasta</span>
        <input
          type="number"
          placeholder="Hasta"
          value={rangeTo}
          onChange={(e) => setRangeTo(e.target.value)}
          disabled={activeFilter === 'search'}
        />
        <button onClick={handleRangeFilter} disabled={activeFilter === 'search'}>
          Aplicar
        </button>
      </div>

      <button 
        onClick={handleClear} 
        disabled={!filterActive}
        className="btn-clear"
      >
        Limpiar filtros
      </button>
    </div>
  );
}

export default FilterControls;