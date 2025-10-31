// --- SISTEMA DE NOTIFICACIONES MEJORADO ---
class NotificationSystem {
    constructor() {
        console.log('🔔 NotificationSystem inicializando...');
        
        // Cargar configuración
        this.settings = this.loadSettings();
        this.notifications = JSON.parse(localStorage.getItem('adminNotifications')) || [];
        this.isPolling = false;
        this.pollingInterval = null;
        this.currentAdmin = authHandler.getUser()?.username;
        
        console.log('👤 Admin actual:', this.currentAdmin);
        console.log('📋 Notificaciones en storage:', this.notifications.length);
        console.log('⚙️ Configuración cargada:', this.settings);
        
        this.initializeElements();
        this.loadCustomSound();
        this.checkExistingCustomSound();
        this.renderNotifications();
        this.startPolling();
        this.setupSettingsModal();
    }

    loadSettings() {
        const defaultSettings = {
            sound: 'default',
            volume: 70,
            autoMarkAsRead: true,
            desktopNotifications: true,
            customSoundUrl: null
        };
        
        const saved = JSON.parse(localStorage.getItem('notificationSettings')) || {};
        return { ...defaultSettings, ...saved };
    }

    saveSettings() {
        localStorage.setItem('notificationSettings', JSON.stringify(this.settings));
        console.log('💾 Configuración guardada:', this.settings);
    }

    initializeElements() {
        // Elementos de notificación
        this.notificationIcon = document.getElementById('notificationIcon');
        this.notificationBadge = document.getElementById('notificationBadge');
        this.notificationPopup = document.getElementById('notificationPopup');
        this.notificationList = document.getElementById('notificationList');
        this.clearAllBtn = document.getElementById('clearAllNotifications');
        this.toastContainer = document.getElementById('toastContainer');

        // Elementos de audio
        this.audioElements = {
            default: document.getElementById('defaultNotificationSound'),
            chime: document.getElementById('chimeNotificationSound'),
            alert: document.getElementById('alertNotificationSound'),
            message: document.getElementById('messageNotificationSound'),
            custom: document.getElementById('customNotificationSound')
        };

        // Configurar volumen
        this.updateAudioVolume();

        console.log('🔍 Elementos de audio cargados:', Object.keys(this.audioElements));

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Toggle popup de notificaciones
        if (this.notificationIcon) {
            this.notificationIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                this.togglePopup();
            });
        }

        // Cerrar popup al hacer click fuera
        document.addEventListener('click', () => {
            if (this.notificationPopup) {
                this.notificationPopup.classList.remove('show');
            }
        });

        // Prevenir que el popup se cierre al hacer click dentro
        if (this.notificationPopup) {
            this.notificationPopup.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

        // Limpiar todas las notificaciones
        if (this.clearAllBtn) {
            this.clearAllBtn.addEventListener('click', () => {
                this.clearAllNotifications();
            });
        }

        // Agregar botón de configuración al icono de notificación
        this.addSettingsButton();
    }

    addSettingsButton() {
        // Crear botón de configuración (engranaje pequeño)
        const settingsBtn = document.createElement('div');
        settingsBtn.className = 'notification-settings-btn';
        settingsBtn.innerHTML = '<i class="fas fa-cog"></i>';
        settingsBtn.title = 'Configurar notificaciones';
        
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.openSettingsModal();
        });

        if (this.notificationIcon) {
            this.notificationIcon.appendChild(settingsBtn);
        }
    }

    setupSettingsModal() {
        // Elementos del modal de configuración
        this.settingsModal = document.getElementById('notificationSettingsModal');
        this.closeSettingsModal = document.getElementById('closeSettingsModal');
        this.soundSelect = document.getElementById('notificationSoundSelect');
        this.customSoundSection = document.getElementById('customSoundSection');
        this.customSoundUpload = document.getElementById('customSoundUpload');
        this.volumeSlider = document.getElementById('notificationVolume');
        this.volumeValue = document.getElementById('volumeValue');
        this.autoMarkAsRead = document.getElementById('autoMarkAsRead');
        this.desktopNotifications = document.getElementById('desktopNotifications');
        this.testSoundBtn = document.getElementById('testNotificationSound');
        this.saveSettingsBtn = document.getElementById('saveNotificationSettings');
        const deleteCustomSound = document.getElementById('deleteCustomSound');
        
        if (deleteCustomSound) {
            deleteCustomSound.addEventListener('click', () => {
                this.deleteCustomSound();
            });
        }

        // Cargar configuración actual en el modal
        this.loadSettingsToModal();

        // Event listeners del modal
        if (this.closeSettingsModal) {
            this.closeSettingsModal.addEventListener('click', () => {
                this.closeSettingsModalFunc();
            });
        }

        if (this.soundSelect) {
            this.soundSelect.addEventListener('change', (e) => {
                this.toggleCustomSoundSection(e.target.value === 'custom');
            });
        }

        if (this.volumeSlider) {
            this.volumeSlider.addEventListener('input', (e) => {
                this.volumeValue.textContent = `${e.target.value}%`;
            });
        }

        if (this.testSoundBtn) {
            this.testSoundBtn.addEventListener('click', () => {
                this.testNotificationSound();
            });
        }

        if (this.saveSettingsBtn) {
            this.saveSettingsBtn.addEventListener('click', () => {
                this.saveNotificationSettings();
            });
        }

        if (this.customSoundUpload) {
            this.customSoundUpload.addEventListener('change', (e) => {
                this.handleCustomSoundUpload(e);
            });
        }

        // Cerrar modal al hacer click fuera
        if (this.settingsModal) {
            this.settingsModal.addEventListener('click', (e) => {
                if (e.target === this.settingsModal) {
                    this.closeSettingsModalFunc();
                }
            });
        }
    }

    async deleteCustomSound() {
        if (!confirm('¿Estás seguro de que quieres eliminar tu sonido personalizado?')) {
            return;
        }

        try {
            const response = await fetch('/api/delete-notification-sound', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: this.currentAdmin })
            });

            const result = await response.json();
            
            if (result.success) {
                this.settings.customSoundPath = null;
                this.settings.sound = 'default';
                this.saveSettings();
                
                // Limpiar elemento de audio
                this.audioElements.custom.src = '';
                
                // Actualizar UI
                if (this.soundSelect) {
                    this.soundSelect.value = 'default';
                }
                this.toggleCustomSoundSection(false);
                this.updateCurrentSoundInfo(null);
                
                this.showToast('Sonido personalizado eliminado', 'success');
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Error eliminando sonido personalizado:', error);
            alert('Error al eliminar el sonido personalizado: ' + error.message);
        }
    }

    loadSettingsToModal() {
        if (!this.soundSelect) return;

        // Cargar valores actuales en el modal
        this.soundSelect.value = this.settings.sound;
        this.volumeSlider.value = this.settings.volume;
        this.volumeValue.textContent = `${this.settings.volume}%`;
        this.autoMarkAsRead.checked = this.settings.autoMarkAsRead;
        this.desktopNotifications.checked = this.settings.desktopNotifications;
        
        this.toggleCustomSoundSection(this.settings.sound === 'custom');
    }

    toggleCustomSoundSection(show) {
        if (this.customSoundSection) {
            this.customSoundSection.style.display = show ? 'block' : 'none';
        }
    }

    openSettingsModal() {
        if (this.settingsModal) {
            this.settingsModal.style.display = 'flex';
        }
    }

    closeSettingsModalFunc() {
        if (this.settingsModal) {
            this.settingsModal.style.display = 'none';
        }
    }

    // método para verificar el sonido personalizado al cargar
    async checkExistingCustomSound() {
        try {
            const response = await fetch(`/api/get-notification-sound?username=${this.currentAdmin}`);
            const result = await response.json();
            
            if (result.success && result.hasCustomSound) {
                this.settings.customSoundPath = result.soundPath;
                this.settings.sound = 'custom';
                this.saveSettings();
                this.loadCustomSound();
                
                // Actualizar la UI
                if (this.soundSelect) {
                    this.soundSelect.value = 'custom';
                    this.toggleCustomSoundSection(true);
                    this.updateCurrentSoundInfo(result.soundPath);
                }
            }
        } catch (error) {
            console.error('Error verificando sonido personalizado:', error);
        }
    }

    updateCurrentSoundInfo(soundPath) {
        const currentSoundInfo = document.getElementById('currentSoundInfo');
        const currentSoundName = document.getElementById('currentSoundName');
        
        if (soundPath) {
            const filename = soundPath.split('/').pop();
            currentSoundName.textContent = filename;
            currentSoundInfo.style.display = 'block';
        } else {
            currentSoundInfo.style.display = 'none';
        }
    }

    async handleCustomSoundUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validar tipo de archivo
        if (!file.type.startsWith('audio/')) {
            alert('Por favor selecciona un archivo de audio válido.');
            return;
        }

        // Validar tamaño (2MB máximo)
        if (file.size > 2 * 1024 * 1024) {
            alert('El archivo es demasiado grande. Máximo 2MB.');
            return;
        }

        try {
            // Crear FormData para enviar el archivo al servidor
            const formData = new FormData();
            formData.append('sound', file);
            formData.append('username', this.currentAdmin);

            const response = await fetch('/api/upload-notification-sound', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Error al subir el sonido');
            }

            const result = await response.json();
            
            if (result.success) {
                // Actualizar la configuración con la nueva ruta del sonido
                this.settings.customSoundPath = result.filePath;
                this.settings.sound = 'custom';
                this.saveSettings();
                
                // Actualizar el elemento de audio
                this.audioElements.custom.src = result.filePath;
                
                console.log('✅ Sonido personalizado subido:', result.filePath);
                this.showToast('Sonido personalizado guardado correctamente', 'success');
                
                // Actualizar el selector en el modal
                if (this.soundSelect) {
                    this.soundSelect.value = 'custom';
                }
            } else {
                throw new Error(result.error || 'Error desconocido');
            }
            
        } catch (error) {
            console.error('Error subiendo sonido personalizado:', error);
            alert('Error al subir el sonido personalizado: ' + error.message);
        }
    }

    testNotificationSound() {
        console.log('🔊 Probando sonido de notificación...');
        this.playNotificationSound(true); // true = es prueba
    }

    saveNotificationSettings() {
        this.settings.sound = this.soundSelect.value;
        this.settings.volume = parseInt(this.volumeSlider.value);
        this.settings.autoMarkAsRead = this.autoMarkAsRead.checked;
        this.settings.desktopNotifications = this.desktopNotifications.checked;

        this.saveSettings();
        this.updateAudioVolume();
        this.closeSettingsModalFunc();
        
        // Mostrar confirmación
        this.showToast('Configuración guardada correctamente', 'success');
    }

    updateAudioVolume() {
        const volume = this.settings.volume / 100;
        Object.values(this.audioElements).forEach(audio => {
            if (audio) audio.volume = volume;
        });
    }

    // Polling para buscar nuevos tickets asignados
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollingInterval = setInterval(async () => {
            await this.checkForNewTickets();
        }, 10000);

        this.checkForNewTickets();
        console.log('🔄 Polling iniciado');
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.isPolling = false;
            console.log('⏹️ Polling detenido');
        }
    }

    async checkForNewTickets() {
        try {
            const response = await fetch(window.APP_CONFIG.getApiUrl() + '/admin/tickets');
            const tickets = await response.json();

            if (!response.ok) throw new Error('Error al obtener tickets');

            const newTickets = tickets.filter(ticket => 
                ticket.ticket_asignado_a === this.currentAdmin && 
                ticket.ticket_est_ticket && 
                ticket.ticket_est_ticket.trim() === 'PE' &&
                !this.notifications.some(notif => notif.ticketId === ticket.ticket_id_ticket)
            );

            newTickets.forEach(ticket => {
                this.addNotification({
                    type: 'new_ticket',
                    title: '🎫 Nuevo Ticket Asignado',
                    message: `Se te ha asignado el ticket: ${ticket.ticket_id_ticket}`,
                    ticketId: ticket.ticket_id_ticket,
                    timestamp: new Date().toISOString(),
                    read: false,
                    ticketData: ticket
                });
            });

        } catch (error) {
            console.error('Error checking for new tickets:', error);
        }
    }

    addNotification(notification) {
        console.log('➕ Agregando notificación:', notification);
        
        // Verificar si ya existe
        const exists = this.notifications.some(notif => 
            notif.ticketId === notification.ticketId && notif.type === notification.type
        );

        if (!exists) {
            this.notifications.unshift(notification);
            this.saveNotifications();
            this.renderNotifications();
            this.showToastNotification(notification);
            this.playNotificationSound();
            
            // Notificación del sistema (si está habilitada)
            if (this.settings.desktopNotifications && 'Notification' in window) {
                this.showDesktopNotification(notification);
            }
        }
    }

    playNotificationSound(isTest = false) {
        console.log('🔊 Reproduciendo sonido...', this.settings.sound);
        
        let audioElement;
        
        if (this.settings.sound === 'custom' && this.audioElements.custom.src) {
            audioElement = this.audioElements.custom;
        } else {
            audioElement = this.audioElements[this.settings.sound];
        }
        
        if (audioElement && (audioElement.src || this.settings.sound !== 'custom')) {
            audioElement.currentTime = 0;
            
            const playPromise = audioElement.play();
            
            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    console.log('❌ Error reproduciendo sonido:', error);
                    if (!isTest) {
                        this.showToast('Error reproduciendo sonido. Haz clic en la página para permitir audio.', 'error');
                    }
                });
            }
        } else {
            console.warn('⚠️ No se pudo encontrar el elemento de audio:', this.settings.sound);
            if (!isTest) {
                this.showToast('No se encontró el sonido configurado', 'warning');
            }
        }
    }

    // método para cargar el sonido personalizado al iniciar
    loadCustomSound() {
        if (this.settings.customSoundPath) {
            this.audioElements.custom.src = this.settings.customSoundPath;
            console.log('🔊 Sonido personalizado cargado:', this.settings.customSoundPath);
        }
    }

    showDesktopNotification(notification) {
        if (Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/favicon.ico',
                tag: notification.ticketId
            });
        } else if (Notification.permission === 'default') {
            // Solicitar permiso
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification(notification.title, {
                        body: notification.message,
                        icon: '/favicon.ico'
                    });
                }
            });
        }
    }

    showToastNotification(notification) {
        if (!this.toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast ${notification.type}`;
        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-title">${notification.title}</div>
                <button class="toast-close">&times;</button>
            </div>
            <div class="toast-message">${notification.message}</div>
            <div class="toast-time">${this.formatTime(notification.timestamp)}</div>
        `;

        this.toastContainer.appendChild(toast);

        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);

        // Cerrar manualmente
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.remove();
        });
    }

    showToast(message, type = 'info') {
        if (!this.toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-message">${message}</div>
        `;

        this.toastContainer.appendChild(toast);

        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 3000);
    }

    renderNotifications() {
        if (!this.notificationBadge || !this.notificationList) return;

        const unreadCount = this.notifications.filter(n => !n.read).length;
        
        // Actualizar badge
        this.notificationBadge.textContent = unreadCount > 9 ? '9+' : unreadCount;
        this.notificationBadge.style.display = unreadCount > 0 ? 'flex' : 'none';

        // Renderizar lista
        if (this.notifications.length === 0) {
            this.notificationList.innerHTML = `
                <div class="empty-notifications">
                    <i class="fas fa-bell-slash"></i>
                    <p>No hay notificaciones</p>
                </div>
            `;
            return;
        }

        this.notificationList.innerHTML = this.notifications.map(notification => `
            <div class="notification-item ${notification.read ? '' : 'unread'}" 
                 data-id="${notification.ticketId}">
                <div class="notification-icon">
                    <i class="fas fa-ticket-alt"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${this.formatTime(notification.timestamp)}</div>
                </div>
                <button class="notification-close" data-id="${notification.ticketId}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');

        // Event listeners
        this.notificationList.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.notification-close')) {
                    const ticketId = item.dataset.id;
                    this.handleNotificationClick(ticketId);
                }
            });
        });

        this.notificationList.querySelectorAll('.notification-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const ticketId = btn.dataset.id;
                this.removeNotification(ticketId);
            });
        });
    }

    handleNotificationClick(ticketId) {
        const notification = this.notifications.find(n => n.ticketId === ticketId);
        if (notification) {
            notification.read = true;
            this.saveNotifications();
            this.renderNotifications();
            
            // Abrir el ticket en el modal
            this.showTicketDetails(ticketId, notification.ticketData);
        }
    }

    removeNotification(ticketId) {
        this.notifications = this.notifications.filter(n => n.ticketId !== ticketId);
        this.saveNotifications();
        this.renderNotifications();
    }

    togglePopup() {
        if (this.notificationPopup) {
            this.notificationPopup.classList.toggle('show');
            if (this.notificationPopup.classList.contains('show') && this.settings.autoMarkAsRead) {
                this.markAllAsRead();
            }
        }
    }

    markAllAsRead() {
        this.notifications.forEach(notification => {
            notification.read = true;
        });
        this.saveNotifications();
        this.renderNotifications();
    }

    clearAllNotifications() {
        this.notifications = [];
        this.saveNotifications();
        this.renderNotifications();
    }

    showTicketDetails(ticketId, ticketData = null) {
        console.log('📋 Abriendo ticket desde notificación:', ticketId);
        // Aquí puedes implementar cómo quieres mostrar los detalles del ticket
        if (ticketData && window.showTicketDetails) {
            // Usar la función global si existe
            window.showTicketDetails(ticketId);
        } else {
            // Mostrar alerta simple
            alert(`Ticket: ${ticketId}\nAsunto: ${ticketData?.ticket_asu_ticket || 'N/A'}\nUsuario: ${ticketData?.ticket_tusua_ticket || 'N/A'}`);
        }
    }

    saveNotifications() {
        localStorage.setItem('adminNotifications', JSON.stringify(this.notifications));
    }

    formatTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Ahora mismo';
        if (minutes < 60) return `Hace ${minutes} min`;
        if (hours < 24) return `Hace ${hours} h`;
        if (days < 7) return `Hace ${days} d`;
        
        return time.toLocaleDateString('es-ES');
    }
}

// --- SISTEMA DE MIS TICKETS ---
document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.APP_CONFIG.API_BASE_URL;
    const user = authHandler.getUser();

    // Security check
    if (!user || user.rol !== 'admin') {
        alert('Acceso denegado. Debes ser un administrador para ver esta página.');
        window.location.href = '/login.html';
        return;
    }

    // --- CONEXIÓN WEBSOCKET ---
    const socket = io(window.APP_CONFIG.getSocketUrl());
    
    // Cuando se conecta el WebSocket
    socket.on('connect', () => {
        console.log('✅ Conectado al servidor WebSocket');
        
        // Registrar al admin como "en línea"
        socket.emit('admin_online', { 
            username: user.username 
        });
    });

    // Escuchar notificaciones de nuevos tickets
    socket.on('new_ticket_notification', (data) => {
        console.log('🔔 Notificación recibida via WebSocket:', data);
        
        // Usar el sistema de notificaciones existente
        if (window.notificationSystem) {
            window.notificationSystem.addNotification({
                type: 'new_ticket',
                title: data.title,
                message: data.message,
                ticketId: data.ticket_id,
                timestamp: new Date().toISOString(),
                read: false
            });
            
            // También actualizar la lista de tickets automáticamente
            setTimeout(() => {
                fetchMyTickets();
            }, 1000);
        }
    });

    // Manejar desconexión
    socket.on('disconnect', () => {
        console.log('❌ Desconectado del servidor WebSocket');
    });

    // Inicializar sistema de notificaciones
    window.notificationSystem = new NotificationSystem();
    
    // Asegurarse de que el polling se detenga al cambiar de página
    window.addEventListener('beforeunload', () => {
        if (window.notificationSystem) {
            window.notificationSystem.stopPolling();
        }
    });

    // Elementos específicos de Mis Tickets
    const themeToggle = document.getElementById('themeToggle');
    const refreshBtn = document.getElementById('refreshBtn');
    const userAvatar = document.getElementById('userAvatar');
    const userName = document.getElementById('userName');
    const ticketList = document.getElementById('ticketList');
    const assignedTickets = document.getElementById('assignedTickets');
    const pendingTickets = document.getElementById('pendingTickets');
    const finishedTickets = document.getElementById('finishedTickets');
    const totalFiles = document.getElementById('totalFiles');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const ticketModal = document.getElementById('ticketModal');
    const closeModal = document.getElementById('closeModal');
    const closeBtn = document.getElementById('closeBtn');
    const finishBtn = document.getElementById('finishBtn');
    const viewFilesBtn = document.getElementById('viewFilesBtn');
    
    let myTickets = [];
    let currentTicket = null;

    // Set user info
    if (user && user.username) {
        userAvatar.textContent = user.username.charAt(0).toUpperCase();
        userName.textContent = user.username;
    }

    // Theme toggle
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            if (document.body.classList.contains('dark-mode')) {
                themeToggle.innerHTML = '<i class="fas fa-sun"></i><span>Modo claro</span>';
            } else {
                themeToggle.innerHTML = '<i class="fas fa-moon"></i><span>Modo oscuro</span>';
            }
        });
    }

    // Refresh button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshBtn.querySelector('i').classList.add('fa-spin');
            fetchMyTickets().finally(() => {
                setTimeout(() => {
                    refreshBtn.querySelector('i').classList.remove('fa-spin');
                }, 500);
            });
        });
    }

    // Filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const filter = this.dataset.filter;
            renderTickets(filter);
        });
    });

    // Modal events
    if (closeModal) closeModal.addEventListener('click', () => ticketModal.style.display = 'none');
    if (closeBtn) closeBtn.addEventListener('click', () => ticketModal.style.display = 'none');
    
    window.addEventListener('click', (e) => {
        if (e.target === ticketModal) ticketModal.style.display = 'none';
    });

    // Finish ticket
    if (finishBtn) finishBtn.addEventListener('click', finishCurrentTicket);

    // View files
    if (viewFilesBtn) viewFilesBtn.addEventListener('click', () => {
        if (currentTicket) {
            window.open(`${API_BASE_URL}/api/tickets/${currentTicket.ticket_id_ticket}/files`, '_blank');
        }
    });

    // Fetch tickets assigned to me
    async function fetchMyTickets() {
        try {
            showLoadingState();

            const response = await fetch(`${API_BASE_URL}/api/admin/tickets`);
            const allTickets = await response.json();

            if (!response.ok) {
                throw new Error(allTickets.error || 'No se pudieron cargar los tickets.');
            }

            // Filtrar tickets asignados al usuario actual
            myTickets = allTickets.filter(ticket => 
                ticket.ticket_asignado_a === user.username
            );

            // Obtener archivos para cada ticket
            for (let ticket of myTickets) {
                try {
                    const filesResponse = await fetch(`${API_BASE_URL}/api/tickets/${ticket.ticket_id_ticket}/files`);
                    if (filesResponse.ok) {
                        ticket.files = await filesResponse.json();
                    } else {
                        ticket.files = [];
                    }
                } catch (error) {
                    ticket.files = [];
                }
            }

            renderTickets('all');
            updateStats();
        } catch (error) {
            showErrorState(error.message);
        }
    }

    function showLoadingState() {
        if (ticketList) {
            ticketList.innerHTML = `
                <tr>
                    <td colspan="6" class="loading" style="text-align: center; padding: 40px;">
                        <i class="fas fa-spinner fa-spin"></i> Cargando mis tickets...
                    </td>
                </tr>
            `;
        }
    }

    function showErrorState(message) {
        if (ticketList) {
            ticketList.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: var(--error); padding: 40px;">
                        <i class="fas fa-exclamation-circle"></i> Error: ${message}
                    </td>
                </tr>
            `;
        }
    }

    function renderTickets(filter = 'all') {
        if (!ticketList) return;

        let filteredTickets = myTickets;
        if (filter !== 'all') {
            filteredTickets = myTickets.filter(ticket => ticket.ticket_est_ticket.trim() === filter);
        }

        if (filteredTickets.length === 0) {
            ticketList.innerHTML = `
                <tr>
                    <td colspan="6" class="no-tickets">
                        <i class="fas fa-inbox"></i>
                        <p>No hay tickets asignados a ti</p>
                    </td>
                </tr>
            `;
            return;
        }

        let ticketsHTML = '';
        filteredTickets.forEach(ticket => {
            const statusClass = `status-${ticket.ticket_est_ticket.trim()}`;
            const statusText = ticket.ticket_est_ticket.trim() === 'FN' ? 'Finalizado' : 'Pendiente';
            const ticketDate = ticket.ticket_fec_ticket ? new Date(ticket.ticket_fec_ticket).toLocaleDateString('es-ES', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }) : 'N/A';

            // Vista previa de archivos
            let filesHTML = '<span>No hay archivos</span>';
            if (ticket.files && ticket.files.length > 0) {
                filesHTML = '<div class="file-preview">';
                ticket.files.slice(0, 3).forEach((file, index) => {
                    const isImage = file.archivo_tip_archivo && file.archivo_tip_archivo.toLowerCase().match(/(jpg|jpeg|png|gif|webp)$/);
                    filesHTML += `
                        <div class="file-preview-item" data-file-id="${file.archivo_cod_archivo}">
                            ${isImage ? 
                                `<img src="${API_BASE_URL}/api/files/${file.archivo_cod_archivo}/view" alt="${file.archivo_nom_archivo}">` :
                                `<div class="file-icon">
                                    <i class="fas fa-file"></i>
                                </div>`
                            }
                            ${index === 2 && ticket.files.length > 3 ? 
                                `<div class="file-count">+${ticket.files.length - 3}</div>` : ''
                            }
                        </div>
                    `;
                });
                filesHTML += '</div>';
            }

            ticketsHTML += `
                <tr class="ticket-row" data-ticket-id="${ticket.ticket_id_ticket}">
                    <td class="ticket-id">${ticket.ticket_id_ticket}</td>
                    <td>
                        <strong>${ticket.ticket_asu_ticket || 'Sin asunto'}</strong>
                        ${ticket.ticket_tip_ticket ? `<br><small style="color: var(--on-surface-light);">${ticket.ticket_tip_ticket}</small>` : ''}
                    </td>
                    <td>${ticket.ticket_tusua_ticket || 'N/D'}</td>
                    <td>${filesHTML}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td>${ticketDate}</td>
                </tr>
            `;
        });
        
        ticketList.innerHTML = ticketsHTML;
                
        // Add event listeners to ticket rows
        document.querySelectorAll('.ticket-row').forEach(row => {
            row.addEventListener('click', (e) => {
                if (!e.target.closest('.file-preview-item')) {
                    const ticketId = row.dataset.ticketId;
                    showTicketDetails(ticketId);
                }
            });
        });

        // Add event listeners to file previews
        document.querySelectorAll('.file-preview-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileId = item.dataset.fileId;
                window.open(`${API_BASE_URL}/api/files/${fileId}/view`, '_blank');
            });
        });
    }

    // Hacer esta función global para que las notificaciones puedan usarla
    window.showTicketDetails = async function showTicketDetails(ticketId) {
        currentTicket = myTickets.find(t => t.ticket_id_ticket === ticketId);
        
        if (!currentTicket || !ticketModal) return;

        const ticketDate = currentTicket.ticket_fec_ticket ? new Date(currentTicket.ticket_fec_ticket).toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }) : 'N/A';

        // Update modal content
        document.getElementById('modalTicketId').textContent = currentTicket.ticket_id_ticket;
        document.getElementById('modalTicketIdValue').textContent = currentTicket.ticket_id_ticket;
        document.getElementById('modalSubject').textContent = currentTicket.ticket_asu_ticket || 'No disponible';
        document.getElementById('modalUser').textContent = currentTicket.ticket_tusua_ticket || 'No disponible';
        document.getElementById('modalAssignedTo').textContent = currentTicket.ticket_asignado_a || 'Sin asignar';
        
        document.getElementById('modalDate').textContent = ticketDate;
        
        // Estado
        const statusText = currentTicket.ticket_est_ticket.trim() === 'FN' ? 'Finalizado' : 'Pendiente';
        document.getElementById('modalStatusValue').textContent = statusText;
        
        const statusElement = document.getElementById('modalStatus');
        statusElement.textContent = statusText;
        statusElement.className = `ticket-status status-${currentTicket.ticket_est_ticket.trim()}`;

        // Información adicional
        let additionalInfo = currentTicket.ticket_des_ticket || 'No hay descripción disponible';
        document.getElementById('modalAdditionalInfo').innerHTML = additionalInfo;

        // Show/hide finish button
        if (finishBtn) {
            finishBtn.style.display = currentTicket.ticket_est_ticket.trim() === 'FN' ? 'none' : 'block';
        }

        // Load files
        loadFilesInModal(currentTicket.files || []);

        // Show modal
        ticketModal.style.display = 'flex';
    }

    function loadFilesInModal(files) {
        const filesContainer = document.getElementById('modalFiles');
        const fileCount = document.getElementById('fileCount');
        
        if (!filesContainer || !fileCount) return;

        fileCount.textContent = files.length;

        if (files.length === 0) {
            filesContainer.innerHTML = '<p style="color: var(--on-surface-light);">No hay archivos adjuntos</p>';
            return;
        }

        let filesHTML = '';
        files.forEach(file => {
            const isImage = file.archivo_tip_archivo && file.archivo_tip_archivo.toLowerCase().match(/(jpg|jpeg|png|gif|webp)$/);
            filesHTML += `
                <div class="file-item">
                    <div class="file-preview" data-file-id="${file.archivo_cod_archivo}">
                        ${isImage ? 
                            `<img src="${API_BASE_URL}/api/files/${file.archivo_cod_archivo}/view" alt="${file.archivo_nom_archivo}">` :
                            `<i class="fas fa-file" style="font-size: 40px; color: var(--primary);"></i>`
                        }
                    </div>
                    <div class="file-info">
                        <div class="file-name" title="${file.archivo_nom_archivo}">${file.archivo_nom_archivo}</div>
                        <div class="file-size">${file.archivo_tam_formateado || 'N/D'}</div>
                    </div>
                </div>
            `;
        });

        filesContainer.innerHTML = filesHTML;

        // Add event listeners to file previews in modal
        filesContainer.querySelectorAll('.file-preview').forEach(preview => {
            preview.addEventListener('click', () => {
                const fileId = preview.dataset.fileId;
                window.open(`${API_BASE_URL}/api/files/${fileId}/view`, '_blank');
            });
        });
    }

    async function finishCurrentTicket() {
        if (!currentTicket || !finishBtn) return;

        const originalText = finishBtn.innerHTML;
        finishBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        finishBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/api/admin/tickets/${currentTicket.ticket_id_ticket}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'FN' })
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Error al finalizar el ticket.');
            }

            // Update local data
            currentTicket.ticket_est_ticket = 'FN';
            const ticketIndex = myTickets.findIndex(t => t.ticket_id_ticket === currentTicket.ticket_id_ticket);
            if (ticketIndex !== -1) {
                myTickets[ticketIndex].ticket_est_ticket = 'FN';
            }

            // Update UI
            finishBtn.style.display = 'none';
            document.getElementById('modalStatus').textContent = 'Finalizado';
            document.getElementById('modalStatus').className = 'ticket-status status-FN';

            // Update table
            renderTickets(document.querySelector('.filter-btn.active').dataset.filter);
            updateStats();

            alert('Ticket finalizado correctamente');

        } catch (error) {
            alert(`Error: ${error.message}`);
            finishBtn.innerHTML = originalText;
            finishBtn.disabled = false;
        }
    }

    function updateStats() {
        if (assignedTickets) assignedTickets.textContent = myTickets.length;
        
        const pending = myTickets.filter(ticket => ticket.ticket_est_ticket.trim() === 'PE').length;
        const finished = myTickets.filter(ticket => ticket.ticket_est_ticket.trim() === 'FN').length;
        
        if (pendingTickets) pendingTickets.textContent = pending;
        if (finishedTickets) finishedTickets.textContent = finished;
        
        // Calculate total files
        if (totalFiles) {
            const totalFilesCount = myTickets.reduce((total, ticket) => {
                return total + (ticket.files ? ticket.files.length : 0);
            }, 0);
            totalFiles.textContent = totalFilesCount;
        }
    }

    // Initialize
    fetchMyTickets();
});