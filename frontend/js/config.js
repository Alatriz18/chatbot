// Configuración centralizada para el frontend
window.APP_CONFIG = {
    // URL base de la API - se determina automáticamente según el entorno
    API_BASE_URL: window.location.origin,
    
    // URLs específicas
    getApiUrl: function() {
        return this.API_BASE_URL + '/api';
    },
    
    getSocketUrl: function() {
        return this.API_BASE_URL;
    },
    
    // Configuración de desarrollo (cuando se ejecuta en localhost)
    isDevelopment: function() {
        return window.location.hostname === 'localhost' || 
               window.location.hostname === '127.0.0.1' ||
               window.location.hostname.includes('192.168.') ||
               window.location.hostname.includes('172.20.');
    },
    
    // Configuración específica para desarrollo local
    DEV_CONFIG: {
        API_BASE_URL: 'http://172.20.8.70:5000'
    }
};

// Si estamos en desarrollo, usar configuración específica
if (window.APP_CONFIG.isDevelopment()) {
    window.APP_CONFIG.API_BASE_URL = window.APP_CONFIG.DEV_CONFIG.API_BASE_URL;
}