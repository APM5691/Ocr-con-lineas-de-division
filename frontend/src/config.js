// Configuración de URLs de los servicios
export const API_CONFIG = {
  BACKEND_URL: "http://localhost:5000",
  PADDLE_URL: "http://localhost:8000",
};

export const getBackendURL = (endpoint) => {
  return `${API_CONFIG.BACKEND_URL}${endpoint}`;
};

export const getPaddleURL = (endpoint) => {
  return `${API_CONFIG.PADDLE_URL}${endpoint}`;
};
