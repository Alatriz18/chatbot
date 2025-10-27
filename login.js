document.addEventListener('DOMContentLoaded', () => {
    // Configuración simple para red local
    const API_BASE_URL = window.location.hostname === '172.20.8.70' 
        ? 'http://172.20.8.70:5000' 
        : `http://${window.location.hostname}:5000`;

    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMessage.style.display = 'none';

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Error de autenticación.');
            }

            sessionStorage.setItem('user', JSON.stringify(result.user));

            // Redirección con rutas relativas
            if (result.user.rol === 'admin') {
                window.location.href = 'admin.html';
            } else {
                window.location.href = 'chat.html';
            }

        } catch (error) {
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.style.display = 'block';
        }
    });
});