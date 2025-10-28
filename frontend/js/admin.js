let allUsers = [];
let allTickets = [];
let currentUser = null;
// --- SISTEMA DE NOTIFICACIONES  ---
class NotificationSystem {
    constructor() {
        console.log('🔔 NotificationSystem inicializando...');
        
        // Cargar configuración
        this.settings = this.loadSettings();
        this.notifications = JSON.parse(localStorage.getItem('adminNotifications')) || [];
        this.isPolling = false;
        this.pollingInterval = null;
        this.currentAdmin = JSON.parse(sessionStorage.getItem('user'))?.username;
        
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
//  método para verificar el sonido personalizado al cargar
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
            
            // Aquí puedes abrir el ticket en un modal o nueva pestaña
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
        console.log('📋 Abriendo ticket:', ticketId);
        // Aquí puedes implementar cómo quieres mostrar los detalles del ticket
        // Por ejemplo: abrir un modal, redirigir, etc.
        if (ticketData) {
            alert(`Ticket: ${ticketId}\nAsunto: ${ticketData.ticket_asu_ticket}\nUsuario: ${ticketData.ticket_tusua_ticket}`);
        } else {
            alert(`Mostrando detalles del ticket: ${ticketId}`);
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


// Agrega esta función para cargar todos los usuarios
async function loadAllUsers() {
    try {
        const response = await fetch('/api/users');
        if (response.ok) {
            allUsers = await response.json();
            console.log('Usuarios cargados:', allUsers.length);
        } else {
            console.error('Error al cargar usuarios:', response.status);
        }
    } catch (error) {
        console.error('Error al cargar usuarios:', error);
    }
}

// Modifica la función renderTickets para hacer la columna de usuario editable
function renderTickets(tickets) {
    const ticketList = document.getElementById('ticketList');
    
    if (!tickets || tickets.length === 0) {
        ticketList.innerHTML = `
            <tr>
                <td colspan="7" class="no-tickets">
                    <i class="fas fa-inbox"></i>
                    <p>No hay tickets disponibles</p>
                </td>
            </tr>
        `;
        return;
    }

    let ticketsHTML = '';
    
    tickets.forEach(ticket => {
        const statusClass = ticket.ticket_est_ticket === 'FN' ? 'status-finished' : 'status-pending';
        const statusText = ticket.ticket_est_ticket === 'FN' ? 'Finalizado' : 'Pendiente';
        const date = new Date(ticket.ticket_fec_ticket).toLocaleDateString('es-ES');
        
        // Generar opciones para el dropdown de usuarios
        const userOptions = allUsers.map(user => 
            `<option value="${user.username}" ${user.username === ticket.ticket_tusua_ticket ? 'selected' : ''}>
                ${user.username}
            </option>`
        ).join('');
        
        ticketsHTML += `
            <tr data-ticket-id="${ticket.ticket_id_ticket}">
                <td class="ticket-id">${ticket.ticket_id_ticket}</td>
                <td class="ticket-subject">${ticket.ticket_asu_ticket}</td>
                <td class="user-cell">
                    <div class="user-display">
                        ${ticket.ticket_tusua_ticket}
                        <i class="fas fa-edit user-edit-icon" data-ticket-id="${ticket.ticket_id_ticket}"></i>
                    </div>
                    <div class="user-edit-controls" style="display: none;">
                        <select class="user-select-dropdown" id="userSelect_${ticket.ticket_id_ticket}">
                            <option value="">Seleccionar usuario...</option>
                            ${userOptions}
                        </select>
                        <button class="save-user-btn" data-ticket-id="${ticket.ticket_id_ticket}">
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="cancel-user-btn" data-ticket-id="${ticket.ticket_id_ticket}">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </td>
                <td class="assigned-to">
                    ${ticket.ticket_asignado_a || 'No asignado'}
                    ${ticket.ticket_asignado_a ? `<i class="fas fa-edit assign-edit-icon" data-ticket-id="${ticket.ticket_id_ticket}"></i>` : ''}
                </td>
                <td>
                    <span class="ticket-status ${statusClass}">${statusText}</span>
                </td>
                <td class="ticket-date">${date}</td>
                <td class="ticket-actions">
                    <button class="btn-icon view-ticket" data-ticket-id="${ticket.ticket_id_ticket}" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon assign-ticket" data-ticket-id="${ticket.ticket_id_ticket}" title="Asignar técnico">
                        <i class="fas fa-user-plus"></i>
                    </button>
                    ${ticket.ticket_est_ticket !== 'FN' ? `
                    <button class="btn-icon finish-ticket" data-ticket-id="${ticket.ticket_id_ticket}" title="Marcar como finalizado">
                        <i class="fas fa-check-circle"></i>
                    </button>
                    ` : ''}
                </td>
            </tr>
        `;
    });
    
    ticketList.innerHTML = ticketsHTML;
    
    // Agregar event listeners para la edición de usuarios
    addUserEditEventListeners();
}

// Función para agregar event listeners a los controles de edición de usuarios
function addUserEditEventListeners() {
    // Event listeners para iconos de edición
    document.querySelectorAll('.user-edit-icon').forEach(icon => {
        icon.addEventListener('click', function(e) {
            e.stopPropagation();
            const ticketId = this.dataset.ticketId;
            showUserEditControls(ticketId);
        });
    });
    
    // Event listeners para botones de guardar
    document.querySelectorAll('.save-user-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const ticketId = this.dataset.ticketId;
            saveUserChange(ticketId);
        });
    });
    
    // Event listeners para botones de cancelar
    document.querySelectorAll('.cancel-user-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const ticketId = this.dataset.ticketId;
            hideUserEditControls(ticketId);
        });
    });
    
    // Event listener para Enter en el dropdown
    document.querySelectorAll('.user-select-dropdown').forEach(select => {
        select.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const ticketId = this.id.replace('userSelect_', '');
                saveUserChange(ticketId);
            }
        });
    });
}

// Función para mostrar controles de edición de usuario
function showUserEditControls(ticketId) {
    const row = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    const displayDiv = row.querySelector('.user-display');
    const editControls = row.querySelector('.user-edit-controls');
    
    displayDiv.style.display = 'none';
    editControls.style.display = 'flex';
    
    // Enfocar el dropdown
    const dropdown = row.querySelector('.user-select-dropdown');
    dropdown.focus();
    
    currentEditingTicket = ticketId;
}

// Función para ocultar controles de edición de usuario
function hideUserEditControls(ticketId) {
    const row = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    const displayDiv = row.querySelector('.user-display');
    const editControls = row.querySelector('.user-edit-controls');
    
    displayDiv.style.display = 'block';
    editControls.style.display = 'none';
    
    currentEditingTicket = null;
}

// Función para guardar el cambio de usuario
async function saveUserChange(ticketId) {
    const row = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    const dropdown = row.querySelector('.user-select-dropdown');
    const newUsername = dropdown.value;
    
    if (!newUsername) {
        showToast('Por favor selecciona un usuario', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/tickets/${ticketId}/reassign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: newUsername
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast(result.message, 'success');
            
            // Actualizar la visualización
            const displayDiv = row.querySelector('.user-display');
            displayDiv.innerHTML = `${newUsername} <i class="fas fa-edit user-edit-icon" data-ticket-id="${ticketId}"></i>`;
            
            hideUserEditControls(ticketId);
            
            // Recargar event listeners
            addUserEditEventListeners();
            
        } else {
            const error = await response.json();
            showToast(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        console.error('Error al reasignar usuario:', error);
        showToast('Error al reasignar usuario', 'error');
    }
}

// Modifica la función loadTickets para cargar también los usuarios
async function loadTickets() {
    try {
        showLoading();
        
        // Cargar usuarios si no están cargados
        if (allUsers.length === 0) {
            await loadAllUsers();
        }
        
        const response = await fetch('/api/admin/tickets');
        if (response.ok) {
            const tickets = await response.json();
            renderTickets(tickets);
            updateStats(tickets);
        } else {
            throw new Error('Error al cargar tickets');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error al cargar tickets', 'error');
    } finally {
        hideLoading();
    }
}


// --- BLOQUE PRINCIPAL DE ADMIN ---
document.addEventListener('DOMContentLoaded', () => {
      loadAllUsers().then(() => {
        loadTickets();
    });
    
    // --- CONFIGURACIÓN DINÁMICA PARA RED LOCAL ---
    // Usar configuración centralizada
    const getApiBaseUrl = () => {
        return window.APP_CONFIG.API_BASE_URL;
    };

    const API_BASE_URL = getApiBaseUrl();
    const ADMIN_API_URL = `${API_BASE_URL}/api/admin`;
    
    console.log('🌐 Admin - Configuración de red detectada:');
    console.log('Hostname:', window.location.hostname);
    console.log('API URL:', API_BASE_URL);

    const user = JSON.parse(sessionStorage.getItem('user'));

    // Si no hay usuario o el rol no es 'admin', lo redirige a la página de login
    if (!user || user.rol !== 'admin') {
        alert('Acceso denegado. Debes ser un administrador para ver esta página.');
        window.location.href = 'login.html';
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
                fetchTickets();
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

    // --- VARIABLES Y ELEMENTOS ---
    const themeToggle = document.getElementById('themeToggle');
    const refreshBtn = document.getElementById('refreshBtn');
    const userAvatar = document.getElementById('userAvatar');
    const userName = document.getElementById('userName');
    const ticketList = document.getElementById('ticketList');
    const totalTickets = document.getElementById('assignedTickets') || document.getElementById('totalTickets');
    const pendingTickets = document.getElementById('pendingTickets');
    const finishedTickets = document.getElementById('finishedTickets');
    const filterButtons = document.querySelectorAll('.filter-btn');
    let allAdmins = [];

    // Set user info
    if (user && user.username) {
        userAvatar.textContent = user.username.charAt(0).toUpperCase();
        userName.textContent = user.username;
    }

    // --- FUNCIONES PRINCIPALES ---

    async function fetchAdmins() {
        try {
            const response = await fetch(window.APP_CONFIG.getApiUrl() + '/admins');
            allAdmins = await response.json();
            if (!response.ok) throw new Error('No se pudo cargar la lista de administradores.');
        } catch (error) {
            console.error(error);
            allAdmins = [];
        }
    }

    async function fetchTickets(filter = 'all') {
        try {
            showLoadingState();
            
            const response = await fetch(`${ADMIN_API_URL}/tickets`);
            const tickets = await response.json();

            if (!response.ok) {
                throw new Error(tickets.error || 'No se pudieron cargar los tickets.');
            }
            
            renderTickets(tickets, filter);
            updateStats(tickets);
        } catch (error) {
            console.error('Error fetching tickets:', error);
            ticketList.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error al cargar los tickets: ${error.message}</p>
                    <button onclick="fetchTickets()" class="btn-retry">
                        <i class="fas fa-redo"></i> Reintentar
                    </button>
                </div>
            `;
        }
    }

    function showLoadingState() {
        ticketList.innerHTML = `
            <tr>
                <td colspan="7" class="loading" style="text-align: center; padding: 40px;">
                    <i class="fas fa-spinner fa-spin"></i> Cargando tickets...
                </td>
            </tr>
        `;
    }

    function renderTickets(tickets, filter = 'all') {
        if (tickets.length === 0) {
            ticketList.innerHTML = `
                <tr>
                    <td colspan="7" class="no-tickets">
                        <i class="fas fa-inbox"></i>
                        <p>No hay tickets para mostrar</p>
                    </td>
                </tr>
            `;
            return;
        }

        let filteredTickets = tickets;
        if (filter !== 'all') {
            filteredTickets = tickets.filter(ticket => ticket.ticket_est_ticket.trim() === filter);
        }

        let ticketsHTML = '';
        filteredTickets.forEach(ticket => {
            const statusClass = `status-${ticket.ticket_est_ticket.trim()}`;
            const statusText = getStatusText(ticket.ticket_est_ticket);
            const ticketDate = ticket.ticket_fec_ticket ? new Date(ticket.ticket_fec_ticket).toLocaleDateString() : 'N/A';
            let assignDropdownHTML = '<span>N/A</span>';
            
            if (allAdmins.length > 0) {
                assignDropdownHTML = `<select class="assign-dropdown" data-ticket-id="${ticket.ticket_id_ticket}">`;
                assignDropdownHTML += `<option value="">Sin Asignar</option>`;
                allAdmins.forEach(admin => {
                    const isSelected = ticket.ticket_asignado_a === admin.username ? 'selected' : '';
                    assignDropdownHTML += `<option value="${admin.username}" ${isSelected}>${admin.username}</option>`;
                });
                assignDropdownHTML += `</select>`;
            }
            
            ticketsHTML += `
                <tr>
                    <td class="ticket-id">${ticket.ticket_id_ticket}</td>
                    <td>${ticket.ticket_asu_ticket}</td>
                    <td>${ticket.ticket_tusua_ticket || 'N/D'}</td>
                    <td>${assignDropdownHTML}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td>${ticketDate}</td>
                    <td>
                        ${ticket.ticket_est_ticket.trim() !== 'FN' ? 
                            `<button class="action-btn btn-close" data-id="${ticket.ticket_id_ticket}">
                                <i class="fas fa-check"></i> Finalizar
                            </button>` : 
                            '<span>-</span>'
                        }
                    </td>
                </tr>
            `;
        });
        
        ticketList.innerHTML = ticketsHTML;
        
        // Add event listeners to action buttons
        document.querySelectorAll('.btn-close').forEach(button => {
            button.addEventListener('click', handleTicketAction);
        });

        // Add event listeners for assign dropdowns
        document.querySelectorAll('.assign-dropdown').forEach(dropdown => {
            dropdown.addEventListener('change', handleAssignChange);
        });
    }

    function getStatusText(status) {
        const statusMap = {
            'PE': 'Pendiente',
            'FN': 'Finalizado',
            'AS': 'Asignado'
        };
        return statusMap[status] || status || 'Pendiente';
    }

    async function handleAssignChange(e) {
        const ticketId = e.target.dataset.ticketId;
        const adminUsername = e.target.value;
        
        try {
            const response = await fetch(`${window.APP_CONFIG.getApiUrl()}/admin/tickets/${ticketId}/assign`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_username: adminUsername })
            });
            
            if (!response.ok) throw new Error('Error al asignar el ticket.');
            
            console.log(`Ticket ${ticketId} asignado a ${adminUsername}`);
        } catch (error) {
            alert(error.message);
            fetchTickets(document.querySelector('.filter-btn.active').dataset.filter);
        }
    }

    async function handleTicketAction(e) {
        const ticketId = e.currentTarget.dataset.id;
        const button = e.currentTarget;
        
        // Store original text
        const originalHTML = button.innerHTML;
        
        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        button.disabled = true;
        
        try {
            const response = await fetch(`${window.APP_CONFIG.getApiUrl()}/admin/tickets/${ticketId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'FN' })
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Error al actualizar el ticket.');
            }
            
            // If successful, reload tickets
            fetchTickets(document.querySelector('.filter-btn.active').dataset.filter);
            
        } catch (error) {
            alert(`Error: ${error.message}`);
            // Restore button state
            button.innerHTML = originalHTML;
            button.disabled = false;
        }
    }

    function updateStats(tickets) {
        totalTickets.textContent = tickets.length;
        
        const pending = tickets.filter(ticket => ticket.ticket_est_ticket.trim() === 'PE').length;
        const finished = tickets.filter(ticket => ticket.ticket_est_ticket.trim() === 'FN').length;
        
        pendingTickets.textContent = pending;
        finishedTickets.textContent = finished;
    }

    // --- EVENT LISTENERS ---

    // Theme toggle
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        
        if (document.body.classList.contains('dark-mode')) {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i><span>Modo claro</span>';
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i><span>Modo oscuro</span>';
        }
    });

    // Refresh button
    refreshBtn.addEventListener('click', function() {
        refreshBtn.querySelector('i').classList.add('fa-spin');
        fetchTickets().finally(() => {
            setTimeout(() => {
                refreshBtn.querySelector('i').classList.remove('fa-spin');
            }, 500);
        });
    });

    // Filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const filter = this.dataset.filter;
            fetchTickets(filter);
        });
    });

    // --- INICIALIZACIÓN ---
    
    async function initialize() {
        await fetchAdmins();
        await fetchTickets();
    }
    
    initialize();

    // Opcional: Recargar automáticamente cada 30 segundos
    setInterval(fetchTickets, 30000);
});