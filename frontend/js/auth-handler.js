/**
 * Auth Handler - Manejo de autenticación con AWS Cognito
 * Procesa tokens del login centralizado y gestiona la sesión
 */

class AuthHandler {
    constructor() {
        // URL del login centralizado
        this.loginUrl = 'https://main.d2ar0ncsvlrfzm.amplifyapp.com/';
        
        // Inicializar al cargar
        this.init();
    }

    init() {
        // Verificar si hay tokens en el hash (viene del login centralizado)
        const hash = window.location.hash.substring(1);
        
        if (hash) {
            console.log('🔑 Tokens detectados en URL');
            this.processTokensFromHash(hash);
        } else {
            // No hay tokens en el hash, verificar sesión existente
            this.checkExistingSession();
        }
    }

    processTokensFromHash(hash) {
        try {
            // Convertir el hash a objeto
            const params = new URLSearchParams(hash);
            
            const accessToken = params.get('access_token');
            const idToken = params.get('id_token');
            const expiresIn = params.get('expires_in');

            if (accessToken && idToken) {
                console.log('✅ Tokens recibidos del login centralizado');

                // Guardar tokens
                this.saveTokens(accessToken, idToken, expiresIn);

                // Limpiar la URL (remover el hash)
                window.history.replaceState(null, null, window.location.pathname);

                // Validar con el backend y obtener datos del usuario
                this.validateAndLoadUser(accessToken);
            } else {
                console.error('❌ Tokens inválidos o incompletos');
                this.redirectToLogin();
            }
        } catch (error) {
            console.error('❌ Error procesando tokens:', error);
            this.redirectToLogin();
        }
    }

    saveTokens(accessToken, idToken, expiresIn) {
        // Guardar en localStorage
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('idToken', idToken);
        
        // Calcular tiempo de expiración
        const expiresAt = Date.now() + (parseInt(expiresIn || 3600) * 1000);
        localStorage.setItem('tokenExpiresAt', expiresAt.toString());
        
        console.log('💾 Tokens guardados en localStorage');
    }

    async validateAndLoadUser(accessToken) {
        try {
            // Llamar al backend para validar el token y obtener datos del usuario
            const response = await fetch('/api/auth/verify', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Token inválido');
            }

            const data = await response.json();
            console.log('✅ Usuario validado:', data.user);

            // Guardar información del usuario
            localStorage.setItem('user', JSON.stringify(data.user));

            // Determinar a dónde redirigir según el rol
            const user = data.user;
            const isAdmin = user.groups && (
                user.groups.includes('admin') || 
                user.groups.includes('Administradores')
            );

            // Si estamos en login.html, redirigir
            if (window.location.pathname === '/' || window.location.pathname === '/login.html') {
                if (isAdmin) {
                    window.location.href = '/admin';
                } else {
                    window.location.href = '/chat';
                }
            }

            // Notificar que la autenticación está completa
            window.dispatchEvent(new CustomEvent('auth:ready', { detail: { user: data.user } }));

        } catch (error) {
            console.error('❌ Error al validar token:', error);
            this.clearSession();
            this.redirectToLogin();
        }
    }

    checkExistingSession() {
        // Verificar si ya existe una sesión válida
        const accessToken = localStorage.getItem('accessToken');
        const expiresAt = localStorage.getItem('tokenExpiresAt');

        if (accessToken && expiresAt) {
            const now = Date.now();
            
            if (now < parseInt(expiresAt)) {
                console.log('✅ Sesión existente válida');
                
                // Cargar datos del usuario
                const userStr = localStorage.getItem('user');
                if (userStr) {
                    const user = JSON.parse(userStr);
                    
                    // Si estamos en login, redirigir al dashboard
                    if (window.location.pathname === '/' || window.location.pathname === '/login.html') {
                        const isAdmin = user.groups && (
                            user.groups.includes('admin') || 
                            user.groups.includes('Administradores')
                        );
                        
                        if (isAdmin) {
                            window.location.href = '/admin';
                        } else {
                            window.location.href = '/chat';
                        }
                    }
                    
                    // Notificar que el usuario está listo
                    window.dispatchEvent(new CustomEvent('auth:ready', { detail: { user } }));
                } else {
                    // No hay datos de usuario, revalidar
                    this.validateAndLoadUser(accessToken);
                }
            } else {
                console.log('⚠️ Sesión expirada');
                this.clearSession();
                this.redirectToLogin();
            }
        } else {
            console.log('⚠️ No hay sesión activa');
            
            // Si NO estamos en la página de login, redirigir
            if (window.location.pathname !== '/' && window.location.pathname !== '/login.html') {
                this.redirectToLogin();
            }
        }
    }

    redirectToLogin() {
        console.log('🔄 Redirigiendo al login centralizado...');
        window.location.href = this.loginUrl;
    }

    clearSession() {
        // Limpiar tokens y datos del usuario
        localStorage.removeItem('accessToken');
        localStorage.removeItem('idToken');
        localStorage.removeItem('tokenExpiresAt');
        localStorage.removeItem('user');
        console.log('🗑️ Sesión limpiada');
    }

    getAccessToken() {
        return localStorage.getItem('accessToken');
    }

    getUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    }

    isAuthenticated() {
        const accessToken = localStorage.getItem('accessToken');
        const expiresAt = localStorage.getItem('tokenExpiresAt');
        
        if (!accessToken || !expiresAt) {
            return false;
        }
        
        return Date.now() < parseInt(expiresAt);
    }

    logout() {
        console.log('👋 Cerrando sesión...');
        this.clearSession();
        this.redirectToLogin();
    }

    // Interceptor para agregar el token a todas las peticiones fetch
    setupFetchInterceptor() {
        const originalFetch = window.fetch;
        const self = this;

        window.fetch = function(...args) {
            let [url, options = {}] = args;

            // Solo agregar token a peticiones a nuestra API
            if (url.startsWith('/api/')) {
                const token = self.getAccessToken();
                
                if (token) {
                    options.headers = options.headers || {};
                    options.headers['Authorization'] = `Bearer ${token}`;
                }
            }

            return originalFetch(url, options);
        };

        console.log('🔧 Interceptor de fetch configurado');
    }
}

// Crear instancia global
const authHandler = new AuthHandler();

// Configurar interceptor de fetch
authHandler.setupFetchInterceptor();

// Exportar para uso global
window.authHandler = authHandler;

console.log('🚀 Auth Handler inicializado');

