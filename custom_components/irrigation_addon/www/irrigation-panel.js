/**
 * Irrigation Panel JavaScript
 * Main dashboard functionality for the Home Assistant Irrigation Addon
 */

class IrrigationPanel {
    constructor() {
        this.hass = null;
        this.config = null;
        this.rooms = {};
        this.sensorData = {};
        this.settings = {};
        this.currentView = 'dashboard';
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }

    async init() {
        try {
            // Show loading screen
            this.showLoading();
            
            // Initialize Home Assistant connection
            await this.initializeHass();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            // Set up real-time updates
            this.setupWebSocket();
            
            // Show main app
            this.showMainApp();
            
            // Render dashboard
            this.renderDashboard();
            
        } catch (error) {
            console.error('Failed to initialize irrigation panel:', error);
            this.showError('Failed to initialize irrigation system: ' + error.message);
        }
    }

    async initializeHass() {
        // Get Home Assistant connection from parent window
        if (window.parent && window.parent.hass) {
            this.hass = window.parent.hass;
        } else {
            throw new Error('Home Assistant connection not available');
        }
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchView(view);
            });
        });

        // Emergency stop
        document.getElementById('emergency-stop').addEventListener('click', () => {
            this.showEmergencyStopConfirmation();
        });

        // Settings button
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.switchView('settings');
        });

        // Retry button
        document.getElementById('retry-button').addEventListener('click', () => {
            this.init();
        });

        // Modal close
        document.getElementById('modal-close').addEventListener('click', () => {
            this.hideModal();
        });

        // Modal overlay click
        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.hideModal();
            }
        });

        // Add room button
        document.getElementById('add-room-btn').addEventListener('click', () => {
            this.showAddRoomModal();
        });
    }

    async loadInitialData() {
        try {
            // Call the coordinator to get current data
            const response = await this.hass.callService('irrigation_addon', 'get_data', {});
            
            if (response && response.data) {
                this.rooms = response.data.rooms || {};
                this.sensorData = response.data.sensor_data || {};
                this.settings = response.data.settings || {};
            } else {
                // Fallback: try to get data from coordinator directly
                const coordinatorData = await this.getCoordinatorData();
                this.rooms = coordinatorData.rooms || {};
                this.sensorData = coordinatorData.sensor_data || {};
                this.settings = coordinatorData.settings || {};
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
            // Initialize with empty data
            this.rooms = {};
            this.sensorData = {};
            this.settings = {};
        }
    }

    async getCoordinatorData() {
        // This would be implemented to directly access coordinator data
        // For now, return empty data structure
        return {
            rooms: {},
            sensor_data: {},
            settings: {}
        };
    }

    setupWebSocket() {
        // Set up WebSocket connection for real-time updates
        this.connectWebSocket();
        
        // Set up periodic data refresh as fallback
        this.setupPeriodicRefresh();
        
        // Handle page visibility changes
        this.setupVisibilityHandling();
    }

    connectWebSocket() {
        if (!this.hass || !this.hass.connection) {
            console.warn('Home Assistant connection not available for WebSocket');
            this.updateWebSocketStatus('disconnected');
            return;
        }

        try {
            this.updateWebSocketStatus('connecting');
            
            // Subscribe to irrigation addon state changes
            this.hass.connection.subscribeEvents((event) => {
                this.handleStateChangeEvent(event);
            }, 'irrigation_addon_state_changed');

            // Subscribe to Home Assistant state changes for entities we care about
            this.hass.connection.subscribeEvents((event) => {
                this.handleEntityStateChange(event);
            }, 'state_changed');

            console.log('WebSocket subscriptions established');
            this.reconnectAttempts = 0;
            this.websocketDisconnected = false;
            this.updateWebSocketStatus('connected');
            
        } catch (error) {
            console.error('Failed to set up WebSocket subscriptions:', error);
            this.handleWebSocketError();
        }
    }

    handleStateChangeEvent(event) {
        try {
            const eventData = event.data;
            
            // Update local data based on event type
            switch (eventData.type) {
                case 'room_status_changed':
                    this.updateRoomStatus(eventData.room_id, eventData.status);
                    break;
                case 'sensor_data_updated':
                    this.updateSensorData(eventData.room_id, eventData.sensor_data);
                    break;
                case 'irrigation_started':
                    this.handleIrrigationStarted(eventData);
                    break;
                case 'irrigation_stopped':
                    this.handleIrrigationStopped(eventData);
                    break;
                case 'irrigation_progress':
                    this.handleIrrigationProgress(eventData);
                    break;
                case 'event_updated':
                    this.handleEventUpdated(eventData);
                    break;
                default:
                    console.log('Unknown irrigation event type:', eventData.type);
            }
            
        } catch (error) {
            console.error('Error handling state change event:', error);
        }
    }

    handleEntityStateChange(event) {
        try {
            const entityId = event.data.entity_id;
            const newState = event.data.new_state;
            
            // Check if this entity belongs to any of our rooms
            Object.entries(this.rooms).forEach(([roomId, room]) => {
                let shouldUpdate = false;
                
                // Check if it's a sensor we're monitoring
                Object.values(room.sensors || {}).forEach(sensorEntity => {
                    if (sensorEntity === entityId) {
                        this.updateEntitySensorData(roomId, entityId, newState);
                        shouldUpdate = true;
                    }
                });
                
                // Check if it's a pump or zone entity
                if (room.pump_entity === entityId || room.zone_entities.includes(entityId)) {
                    this.updateEntityHardwareState(roomId, entityId, newState);
                    shouldUpdate = true;
                }
                
                // Check if it's a light entity
                if (room.light_entity === entityId) {
                    this.updateEntityLightState(roomId, entityId, newState);
                    shouldUpdate = true;
                }
                
                if (shouldUpdate && this.currentView === 'dashboard') {
                    this.updateRoomCard(roomId);
                }
            });
            
        } catch (error) {
            console.error('Error handling entity state change:', error);
        }
    }

    updateRoomStatus(roomId, status) {
        // Update internal status tracking
        if (!this.roomStatuses) {
            this.roomStatuses = {};
        }
        this.roomStatuses[roomId] = status;
        
        // Update UI if on dashboard
        if (this.currentView === 'dashboard') {
            this.updateRoomCard(roomId);
        }
        
        // Show toast notifications for important status changes
        if (status.active_irrigation && !this.lastKnownStatuses?.[roomId]?.active_irrigation) {
            this.showToast(`Irrigation started in ${this.rooms[roomId]?.name || roomId}`, 'info');
        }
        
        if (!status.active_irrigation && this.lastKnownStatuses?.[roomId]?.active_irrigation) {
            this.showToast(`Irrigation completed in ${this.rooms[roomId]?.name || roomId}`, 'success');
        }
        
        // Store last known status
        if (!this.lastKnownStatuses) {
            this.lastKnownStatuses = {};
        }
        this.lastKnownStatuses[roomId] = { ...status };
    }

    updateSensorData(roomId, sensorData) {
        // Update internal sensor data
        if (!this.sensorData) {
            this.sensorData = {};
        }
        this.sensorData[roomId] = { ...this.sensorData[roomId], ...sensorData };
        
        // Update UI if on dashboard
        if (this.currentView === 'dashboard') {
            this.updateRoomSensors(roomId);
        }
    }

    updateEntitySensorData(roomId, entityId, state) {
        if (!state || !this.sensorData[roomId]) return;
        
        // Find which sensor type this entity represents
        const room = this.rooms[roomId];
        if (!room || !room.sensors) return;
        
        const sensorType = Object.keys(room.sensors).find(type => room.sensors[type] === entityId);
        if (!sensorType) return;
        
        // Update sensor data
        if (!this.sensorData[roomId]) {
            this.sensorData[roomId] = {};
        }
        
        this.sensorData[roomId][sensorType] = {
            value: state.state !== 'unavailable' && state.state !== 'unknown' ? parseFloat(state.state) : null,
            unit: state.attributes?.unit_of_measurement,
            last_updated: state.last_updated,
            unavailable: state.state === 'unavailable'
        };
        
        // Update UI
        if (this.currentView === 'dashboard') {
            this.updateRoomSensors(roomId);
        }
    }

    updateEntityHardwareState(roomId, entityId, state) {
        // This could be used to show real-time hardware status
        // For now, just log the change
        console.log(`Hardware state changed for ${entityId} in room ${roomId}:`, state.state);
    }

    updateEntityLightState(roomId, entityId, state) {
        // This could be used to show light schedule status
        console.log(`Light state changed for ${entityId} in room ${roomId}:`, state.state);
    }

    handleIrrigationStarted(eventData) {
        const { room_id, event_type, manual } = eventData;
        
        this.showToast(
            `${manual ? 'Manual' : event_type} irrigation started in ${this.rooms[room_id]?.name || room_id}`,
            'info'
        );
        
        // Start progress tracking
        this.startRoomProgressTracking(room_id);
        
        // Update room card
        if (this.currentView === 'dashboard') {
            this.updateRoomCard(room_id);
        }
    }

    handleIrrigationStopped(eventData) {
        const { room_id, success, reason } = eventData;
        
        this.showToast(
            success ? 
                `Irrigation completed in ${this.rooms[room_id]?.name || room_id}` :
                `Irrigation stopped in ${this.rooms[room_id]?.name || room_id}: ${reason}`,
            success ? 'success' : 'warning'
        );
        
        // Stop progress tracking
        this.stopRoomProgressTracking(room_id);
        
        // Update room card
        if (this.currentView === 'dashboard') {
            this.updateRoomCard(room_id);
        }
    }

    handleIrrigationProgress(eventData) {
        const { room_id, progress, current_shot, total_shots, time_remaining } = eventData;
        
        // Update progress tracking data
        if (!this.progressData) {
            this.progressData = {};
        }
        
        this.progressData[room_id] = {
            progress,
            current_shot,
            total_shots,
            time_remaining
        };
        
        // Update progress bar if visible
        if (this.currentView === 'dashboard') {
            this.updateRoomProgress(room_id);
        }
    }

    handleEventUpdated(eventData) {
        const { room_id, event_type, action } = eventData;
        
        // Refresh events view if currently visible
        if (this.currentView === 'events') {
            setTimeout(() => this.renderEvents(), 500);
        }
        
        // Show notification
        this.showToast(`Event ${event_type} ${action} for ${this.rooms[room_id]?.name || room_id}`, 'info');
    }

    updateRoomCard(roomId) {
        const card = document.querySelector(`[data-room-id="${roomId}"]`);
        if (!card) return;
        
        const room = this.rooms[roomId];
        if (!room) return;
        
        // Get updated status
        const status = this.getRoomStatus(roomId);
        
        // Update room status indicator
        const statusElement = card.querySelector('.room-status');
        if (statusElement) {
            statusElement.className = `room-status ${this.getRoomStatusClass(status)}`;
            statusElement.innerHTML = `
                <span class="status-indicator"></span>
                ${this.getRoomStatusText(status)}
            `;
        }
        
        // Update progress bar
        const progressContainer = card.querySelector('.progress-container');
        const newProgressHtml = this.renderProgressBar(status);
        
        if (progressContainer && newProgressHtml) {
            progressContainer.outerHTML = newProgressHtml;
            this.setupRoomCardEventListeners(card, roomId);
        } else if (!progressContainer && newProgressHtml) {
            // Add progress bar if it doesn't exist
            const controlsElement = card.querySelector('.room-controls');
            if (controlsElement) {
                controlsElement.insertAdjacentHTML('beforebegin', newProgressHtml);
                this.setupRoomCardEventListeners(card, roomId);
            }
        } else if (progressContainer && !newProgressHtml) {
            // Remove progress bar if no longer needed
            progressContainer.remove();
        }
        
        // Update control buttons
        const stopBtn = card.querySelector('.stop-btn');
        if (stopBtn) {
            stopBtn.disabled = !status.active_irrigation && !status.manual_run;
        }
        
        // Update card styling
        if (status.active_irrigation || status.manual_run) {
            card.classList.add('active-irrigation');
        } else {
            card.classList.remove('active-irrigation');
        }
    }

    updateRoomSensors(roomId) {
        const card = document.querySelector(`[data-room-id="${roomId}"]`);
        if (!card) return;
        
        const sensorContainer = card.querySelector('.sensor-data');
        if (!sensorContainer) return;
        
        const sensors = this.sensorData[roomId] || {};
        sensorContainer.innerHTML = this.renderSensorData(sensors);
    }

    setupPeriodicRefresh() {
        // Refresh data every 30 seconds as fallback
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, 30000);
    }

    async refreshData() {
        try {
            // Only refresh if page is visible
            if (document.hidden) return;
            
            // Call coordinator for updated data
            const response = await this.hass.callService('irrigation_addon', 'get_data', {});
            
            if (response && response.data) {
                const hasChanges = JSON.stringify(this.rooms) !== JSON.stringify(response.data.rooms) ||
                                 JSON.stringify(this.sensorData) !== JSON.stringify(response.data.sensor_data);
                
                if (hasChanges) {
                    this.rooms = response.data.rooms || {};
                    this.sensorData = response.data.sensor_data || {};
                    this.settings = response.data.settings || {};
                    
                    // Update current view
                    switch (this.currentView) {
                        case 'dashboard':
                            this.renderDashboard();
                            break;
                        case 'events':
                            this.renderEvents();
                            break;
                    }
                }
            }
            
        } catch (error) {
            console.error('Failed to refresh data:', error);
            this.handleConnectionError();
        }
    }

    setupVisibilityHandling() {
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Page became visible, refresh data
                this.refreshData();
                
                // Reconnect WebSocket if needed
                if (this.websocketDisconnected) {
                    this.connectWebSocket();
                }
            }
        });
        
        // Handle window focus/blur
        window.addEventListener('focus', () => {
            this.refreshData();
        });
    }

    handleWebSocketError() {
        this.websocketDisconnected = true;
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            // Try to reconnect after delay
            setTimeout(() => {
                console.log(`Attempting WebSocket reconnection (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connectWebSocket();
            }, Math.pow(2, this.reconnectAttempts) * 1000); // Exponential backoff
        } else {
            console.warn('Max WebSocket reconnection attempts reached, falling back to periodic refresh');
            this.showToast('Real-time updates unavailable, using periodic refresh', 'warning');
        }
    }

    handleConnectionError() {
        // Show connection error indicator
        const statusIndicator = document.getElementById('system-status-indicator');
        const statusText = document.getElementById('system-status-text');
        
        if (statusIndicator && statusText) {
            statusIndicator.className = 'status-indicator status-warning';
            statusText.textContent = 'Connection Issues';
        }
        
        // Try to reconnect
        setTimeout(() => {
            this.refreshData();
        }, 5000);
    }

    // Override getRoomStatus to use real-time data when available
    getRoomStatus(roomId) {
        // Use real-time status if available
        if (this.roomStatuses && this.roomStatuses[roomId]) {
            return this.roomStatuses[roomId];
        }
        
        // Fallback to default status
        return {
            active_irrigation: false,
            manual_run: false,
            daily_total: 0,
            next_events: {},
            last_events: {}
        };
    }

    updateWebSocketStatus(status) {
        const indicator = document.getElementById('websocket-indicator');
        const text = document.getElementById('websocket-text');
        
        if (!indicator || !text) return;
        
        // Remove all status classes
        indicator.classList.remove('disconnected', 'reconnecting');
        
        switch (status) {
            case 'connected':
                text.textContent = 'Live';
                break;
            case 'connecting':
            case 'reconnecting':
                indicator.classList.add('reconnecting');
                text.textContent = 'Connecting...';
                break;
            case 'disconnected':
                indicator.classList.add('disconnected');
                text.textContent = 'Offline';
                break;
        }
    }

    // Enhanced error handling with user feedback
    handleWebSocketError() {
        this.websocketDisconnected = true;
        this.reconnectAttempts++;
        this.updateWebSocketStatus('disconnected');
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            // Try to reconnect after delay
            this.updateWebSocketStatus('reconnecting');
            setTimeout(() => {
                console.log(`Attempting WebSocket reconnection (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connectWebSocket();
            }, Math.pow(2, this.reconnectAttempts) * 1000); // Exponential backoff
        } else {
            console.warn('Max WebSocket reconnection attempts reached, falling back to periodic refresh');
            this.showToast('Real-time updates unavailable, using periodic refresh', 'warning');
            this.updateWebSocketStatus('disconnected');
        }
    }

    // Enhanced connection error handling
    handleConnectionError() {
        // Show connection error indicator
        const statusIndicator = document.getElementById('system-status-indicator');
        const statusText = document.getElementById('system-status-text');
        
        if (statusIndicator && statusText) {
            statusIndicator.className = 'status-indicator status-warning';
            statusText.textContent = 'Connection Issues';
        }
        
        this.updateWebSocketStatus('disconnected');
        
        // Try to reconnect
        setTimeout(() => {
            this.refreshData();
        }, 5000);
    }

    // Add visual feedback for real-time updates
    addUpdateAnimation(element) {
        if (!element) return;
        
        element.classList.add('updating');
        setTimeout(() => {
            element.classList.remove('updating');
        }, 1500);
    }

    // Enhanced sensor update with animation
    updateRoomSensors(roomId) {
        const card = document.querySelector(`[data-room-id="${roomId}"]`);
        if (!card) return;
        
        const sensorContainer = card.querySelector('.sensor-data');
        if (!sensorContainer) return;
        
        const sensors = this.sensorData[roomId] || {};
        sensorContainer.innerHTML = this.renderSensorData(sensors);
        
        // Add update animation
        this.addUpdateAnimation(card);
        
        // Add animation to individual sensor items
        sensorContainer.querySelectorAll('.sensor-item').forEach(item => {
            item.classList.add('updated');
            setTimeout(() => {
                item.classList.remove('updated');
            }, 500);
        });
    }

    // Enhanced room card update with animations
    updateRoomCard(roomId) {
        const card = document.querySelector(`[data-room-id="${roomId}"]`);
        if (!card) return;
        
        const room = this.rooms[roomId];
        if (!room) return;
        
        // Add update animation
        this.addUpdateAnimation(card);
        
        // Get updated status
        const status = this.getRoomStatus(roomId);
        
        // Update room status indicator
        const statusElement = card.querySelector('.room-status');
        if (statusElement) {
            statusElement.className = `room-status ${this.getRoomStatusClass(status)}`;
            statusElement.innerHTML = `
                <span class="status-indicator"></span>
                ${this.getRoomStatusText(status)}
            `;
        }
        
        // Update progress bar
        const progressContainer = card.querySelector('.progress-container');
        const newProgressHtml = this.renderProgressBar(status);
        
        if (progressContainer && newProgressHtml) {
            progressContainer.outerHTML = newProgressHtml;
            this.setupRoomCardEventListeners(card, roomId);
            
            // Add live animation to progress bar
            const newProgressFill = card.querySelector('.progress-fill');
            if (newProgressFill) {
                newProgressFill.classList.add('live');
            }
        } else if (!progressContainer && newProgressHtml) {
            // Add progress bar if it doesn't exist
            const controlsElement = card.querySelector('.room-controls');
            if (controlsElement) {
                controlsElement.insertAdjacentHTML('beforebegin', newProgressHtml);
                this.setupRoomCardEventListeners(card, roomId);
                
                // Add live animation to progress bar
                const newProgressFill = card.querySelector('.progress-fill');
                if (newProgressFill) {
                    newProgressFill.classList.add('live');
                }
            }
        } else if (progressContainer && !newProgressHtml) {
            // Remove progress bar if no longer needed
            progressContainer.remove();
        }
        
        // Update control buttons
        const stopBtn = card.querySelector('.stop-btn');
        if (stopBtn) {
            stopBtn.disabled = !status.active_irrigation && !status.manual_run;
        }
        
        // Update card styling
        if (status.active_irrigation || status.manual_run) {
            card.classList.add('active-irrigation');
        } else {
            card.classList.remove('active-irrigation');
        }
    }

    // Cleanup method
    cleanup() {
        // Clear intervals
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Clear progress tracking intervals
        if (this.progressIntervals) {
            Object.values(this.progressIntervals).forEach(interval => {
                clearInterval(interval);
            });
        }
        
        // Remove event listeners
        document.removeEventListener('visibilitychange', this.visibilityHandler);
        window.removeEventListener('focus', this.focusHandler);
    }

    showLoading() {
        document.getElementById('loading-screen').classList.remove('hidden');
        document.getElementById('error-screen').classList.add('hidden');
        document.getElementById('main-app').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('error-message').textContent = message;
        document.getElementById('loading-screen').classList.add('hidden');
        document.getElementById('error-screen').classList.remove('hidden');
        document.getElementById('main-app').classList.add('hidden');
    }

    showMainApp() {
        document.getElementById('loading-screen').classList.add('hidden');
        document.getElementById('error-screen').classList.add('hidden');
        document.getElementById('main-app').classList.remove('hidden');
    }

    switchView(viewName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewName}"]`).classList.add('active');

        // Update views
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewName}-view`).classList.add('active');

        this.currentView = viewName;

        // Render the appropriate view
        switch (viewName) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'events':
                this.renderEvents();
                break;
            case 'history':
                this.renderHistory();
                break;
            case 'settings':
                this.renderSettings();
                break;
        }
    }

    renderDashboard() {
        const container = document.getElementById('rooms-container');
        const noRooms = document.getElementById('no-rooms');

        if (Object.keys(this.rooms).length === 0) {
            container.innerHTML = '';
            noRooms.classList.remove('hidden');
            return;
        }

        noRooms.classList.add('hidden');
        container.innerHTML = '';

        // Render room cards
        Object.entries(this.rooms).forEach(([roomId, room]) => {
            const roomCard = this.createRoomCard(roomId, room);
            container.appendChild(roomCard);
        });

        // Update system status
        this.updateSystemStatus();
    }

    createRoomCard(roomId, room) {
        const card = document.createElement('div');
        card.className = 'room-card';
        card.dataset.roomId = roomId;

        // Get room status
        const status = this.getRoomStatus(roomId);
        const sensors = this.sensorData[roomId] || {};

        // Add active irrigation class if needed
        if (status.active_irrigation || status.manual_run) {
            card.classList.add('active-irrigation');
        }

        card.innerHTML = `
            <div class="room-header">
                <h3 class="room-title">${this.escapeHtml(room.name)}</h3>
                <div class="room-status ${this.getRoomStatusClass(status)}">
                    <span class="status-indicator"></span>
                    ${this.getRoomStatusText(status)}
                </div>
            </div>

            <div class="sensor-data">
                ${this.renderSensorData(sensors)}
            </div>

            ${this.renderProgressBar(status)}

            <div class="room-controls">
                <button class="btn btn-success manual-run-btn" data-room-id="${roomId}">
                    <span class="icon">▶️</span>
                    Manual Run
                </button>
                <button class="btn btn-danger stop-btn" data-room-id="${roomId}" ${!status.active_irrigation && !status.manual_run ? 'disabled' : ''}>
                    <span class="icon">⏹️</span>
                    Stop
                </button>
                <button class="btn btn-secondary edit-btn" data-room-id="${roomId}">
                    <span class="icon">✏️</span>
                    Edit
                </button>
            </div>

            <div class="event-info">
                ${this.renderEventInfo(status)}
            </div>
        `;

        // Add event listeners for room controls
        this.setupRoomCardEventListeners(card, roomId);

        return card;
    }

    setupRoomCardEventListeners(card, roomId) {
        // Manual run button
        const manualRunBtn = card.querySelector('.manual-run-btn');
        manualRunBtn.addEventListener('click', () => {
            this.showManualRunModal(roomId);
        });

        // Stop button
        const stopBtn = card.querySelector('.stop-btn');
        stopBtn.addEventListener('click', () => {
            this.showStopConfirmation(roomId);
        });

        // Edit button
        const editBtn = card.querySelector('.edit-btn');
        editBtn.addEventListener('click', () => {
            this.showEditRoomModal(roomId);
        });

        // Emergency stop button (if present in progress bar)
        const emergencyStopBtn = card.querySelector('.emergency-stop-room');
        if (emergencyStopBtn) {
            emergencyStopBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showEmergencyStopRoomConfirmation(roomId);
            });
        }
    }

    renderSensorData(sensors) {
        const sensorTypes = [
            { key: 'soil_rh', label: 'Soil RH', unit: '%' },
            { key: 'temperature', label: 'Temp', unit: '°C' },
            { key: 'ec', label: 'EC', unit: 'µS/cm' }
        ];

        return sensorTypes.map(sensor => {
            const data = sensors[sensor.key];
            let valueHtml = '';

            if (data && data.value !== null && !data.unavailable) {
                valueHtml = `
                    <div class="sensor-value">
                        ${data.value}
                        <span class="sensor-unit">${data.unit || sensor.unit}</span>
                    </div>
                `;
            } else {
                valueHtml = `<div class="sensor-value sensor-unavailable">N/A</div>`;
            }

            return `
                <div class="sensor-item">
                    <div class="sensor-label">${sensor.label}</div>
                    ${valueHtml}
                </div>
            `;
        }).join('');
    }

    renderProgressBar(status) {
        if (!status.active_irrigation && !status.manual_run) {
            return '';
        }

        let progress = 0;
        let label = '';
        let timeRemaining = '';
        let progressClass = '';

        if (status.active_irrigation_details) {
            const details = status.active_irrigation_details;
            progress = details.progress || 0;
            label = `${details.event_type} Event - Shot ${details.current_shot + 1}/${details.total_shots}`;
            
            // Calculate time remaining for current shot
            if (details.shot_start_time && details.shot_duration) {
                const elapsed = (Date.now() - new Date(details.shot_start_time).getTime()) / 1000;
                const remaining = Math.max(0, details.shot_duration - elapsed);
                timeRemaining = `${Math.ceil(remaining)}s remaining in shot`;
            }
            progressClass = 'scheduled-irrigation';
            
        } else if (status.manual_run_details) {
            const details = status.manual_run_details;
            const startTime = new Date(details.start_time).getTime();
            const elapsed = (Date.now() - startTime) / 1000;
            progress = Math.min(elapsed / details.duration, 1);
            
            const remaining = Math.max(0, details.duration - elapsed);
            label = 'Manual Run';
            timeRemaining = `${this.formatDuration(Math.ceil(remaining))} remaining`;
            progressClass = 'manual-irrigation';
        }

        return `
            <div class="progress-container ${progressClass}">
                <div class="progress-header">
                    <div class="progress-label">
                        <span class="progress-title">${label}</span>
                        <span class="progress-percentage">${Math.round(progress * 100)}%</span>
                    </div>
                    <div class="progress-time">
                        ${timeRemaining}
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress * 100}%"></div>
                </div>
                <div class="progress-actions">
                    <button class="btn btn-sm btn-danger emergency-stop-room" data-room-id="${status.room_id || ''}">
                        <span class="icon">🛑</span>
                        Emergency Stop
                    </button>
                </div>
            </div>
        `;
    }

    renderEventInfo(status) {
        const nextEvents = status.next_events || {};
        const lastEvents = status.last_events || {};

        return `
            <div class="event-item">
                <div class="event-label">Next P1 Event</div>
                <div class="event-value">${this.formatDateTime(nextEvents.P1) || 'Not scheduled'}</div>
            </div>
            <div class="event-item">
                <div class="event-label">Next P2 Event</div>
                <div class="event-value">${this.formatDateTime(nextEvents.P2) || 'Not scheduled'}</div>
            </div>
            <div class="event-item">
                <div class="event-label">Last P1 Event</div>
                <div class="event-value">${this.formatDateTime(lastEvents.P1) || 'Never'}</div>
            </div>
            <div class="event-item">
                <div class="event-label">Last P2 Event</div>
                <div class="event-value">${this.formatDateTime(lastEvents.P2) || 'Never'}</div>
            </div>
        `;
    }

    getRoomStatus(roomId) {
        // This would normally come from the coordinator
        // For now, return a default status
        return {
            active_irrigation: false,
            manual_run: false,
            daily_total: 0,
            next_events: {},
            last_events: {}
        };
    }

    getRoomStatusClass(status) {
        if (status.active_irrigation) return 'irrigating';
        if (status.manual_run) return 'manual';
        return 'idle';
    }

    getRoomStatusText(status) {
        if (status.active_irrigation) return 'Irrigating';
        if (status.manual_run) return 'Manual Run';
        return 'Idle';
    }

    updateSystemStatus() {
        const indicator = document.getElementById('system-status-indicator');
        const text = document.getElementById('system-status-text');

        // Calculate system health
        const totalRooms = Object.keys(this.rooms).length;
        const activeIrrigations = Object.values(this.rooms).filter(room => 
            this.getRoomStatus(room.room_id).active_irrigation
        ).length;

        if (totalRooms === 0) {
            indicator.className = 'status-indicator status-warning';
            text.textContent = 'No Rooms Configured';
        } else if (activeIrrigations > 0) {
            indicator.className = 'status-indicator status-healthy';
            text.textContent = `${activeIrrigations} Active Irrigation${activeIrrigations > 1 ? 's' : ''}`;
        } else {
            indicator.className = 'status-indicator status-healthy';
            text.textContent = 'System Healthy';
        }
    }

    // Modal Functions
    showModal(title, content, buttons = []) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = content;
        
        const footer = document.getElementById('modal-footer');
        footer.innerHTML = '';
        
        buttons.forEach(button => {
            const btn = document.createElement('button');
            btn.className = `btn ${button.class || 'btn-secondary'}`;
            btn.textContent = button.text;
            btn.addEventListener('click', button.onClick);
            footer.appendChild(btn);
        });

        document.getElementById('modal-overlay').classList.remove('hidden');
    }

    hideModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }

    showManualRunModal(roomId) {
        const room = this.rooms[roomId];
        if (!room) return;

        // Check if irrigation is already active
        const status = this.getRoomStatus(roomId);
        if (status.active_irrigation || status.manual_run) {
            this.showToast('Irrigation is already active for this room', 'warning');
            return;
        }

        const content = `
            <div class="form-group">
                <label class="form-label">Room: ${this.escapeHtml(room.name)}</label>
                <div style="font-size: 0.9rem; color: #666; margin-top: 5px;">
                    Pump: ${this.escapeHtml(room.pump_entity)}<br>
                    Zones: ${room.zone_entities.length} configured
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="manual-duration">Duration</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="number" id="manual-duration-minutes" class="form-input" 
                           min="0" max="60" value="5" placeholder="Minutes" style="flex: 1;">
                    <span>:</span>
                    <input type="number" id="manual-duration-seconds" class="form-input" 
                           min="0" max="59" value="0" placeholder="Seconds" style="flex: 1;">
                </div>
                <small style="color: #666; margin-top: 5px; display: block;">
                    Maximum duration: 1 hour. Current daily usage: ${this.formatDuration(status.daily_total || 0)}
                </small>
            </div>

            <div class="form-group">
                <label class="form-label">
                    <input type="checkbox" id="override-failsafe" style="margin-right: 8px;">
                    Override fail-safe checks (Advanced)
                </label>
                <small style="color: #d32f2f; margin-top: 5px; display: block;">
                    ⚠️ Only check this if you understand the risks
                </small>
            </div>

            <div class="manual-run-preview" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px;">
                <h4 style="margin-bottom: 10px; color: #333;">Irrigation Sequence Preview:</h4>
                <ol style="margin-left: 20px; color: #666;">
                    <li>Activate pump (${this.escapeHtml(room.pump_entity)})</li>
                    <li>Wait 3 seconds for pump stabilization</li>
                    <li>Activate zones (${room.zone_entities.length} zones)</li>
                    <li>Run irrigation for specified duration</li>
                    <li>Deactivate zones</li>
                    <li>Deactivate pump</li>
                </ol>
            </div>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Start Manual Run',
                class: 'btn-success',
                onClick: () => this.startManualRun(roomId)
            }
        ];

        this.showModal('Manual Irrigation Run', content, buttons);

        // Add real-time duration calculation
        const minutesInput = document.getElementById('manual-duration-minutes');
        const secondsInput = document.getElementById('manual-duration-seconds');
        
        const updatePreview = () => {
            const minutes = parseInt(minutesInput.value) || 0;
            const seconds = parseInt(secondsInput.value) || 0;
            const totalSeconds = minutes * 60 + seconds;
            
            // Update button text with duration
            const startButton = document.querySelector('.modal-footer .btn-success');
            if (startButton) {
                startButton.textContent = `Start Manual Run (${this.formatDuration(totalSeconds)})`;
            }
        };

        minutesInput.addEventListener('input', updatePreview);
        secondsInput.addEventListener('input', updatePreview);
        updatePreview();
    }

    async startManualRun(roomId) {
        const minutes = parseInt(document.getElementById('manual-duration-minutes').value) || 0;
        const seconds = parseInt(document.getElementById('manual-duration-seconds').value) || 0;
        const duration = minutes * 60 + seconds;
        const overrideFailsafe = document.getElementById('override-failsafe').checked;
        
        if (duration < 1 || duration > 3600) {
            this.showToast('Invalid duration. Please enter a value between 1 second and 1 hour.', 'error');
            return;
        }

        // Show confirmation for long durations
        if (duration > 1800) { // 30 minutes
            const confirmed = confirm(`Are you sure you want to run irrigation for ${this.formatDuration(duration)}? This is a long duration.`);
            if (!confirmed) return;
        }

        try {
            // Show loading state
            const startButton = document.querySelector('.modal-footer .btn-success');
            const originalText = startButton.textContent;
            startButton.textContent = 'Starting...';
            startButton.disabled = true;

            await this.hass.callService('irrigation_addon', 'start_manual_run', {
                room_id: roomId,
                duration: duration,
                override_failsafe: overrideFailsafe
            });

            this.hideModal();
            this.showToast(`Manual irrigation started for ${this.formatDuration(duration)}`, 'success');
            
            // Start real-time updates for this room
            this.startRoomProgressTracking(roomId);
            
            // Refresh dashboard
            setTimeout(() => this.renderDashboard(), 1000);
            
        } catch (error) {
            console.error('Failed to start manual run:', error);
            this.showToast('Failed to start manual irrigation: ' + error.message, 'error');
            
            // Reset button state
            const startButton = document.querySelector('.modal-footer .btn-success');
            if (startButton) {
                startButton.textContent = originalText;
                startButton.disabled = false;
            }
        }
    }

    async stopIrrigation(roomId) {
        try {
            await this.hass.callService('irrigation_addon', 'stop_irrigation', {
                room_id: roomId
            });

            this.showToast('Irrigation stopped successfully', 'success');
            
            // Refresh dashboard
            setTimeout(() => this.renderDashboard(), 1000);
            
        } catch (error) {
            console.error('Failed to stop irrigation:', error);
            this.showToast('Failed to stop irrigation: ' + error.message, 'error');
        }
    }

    showEmergencyStopConfirmation() {
        const content = `
            <p style="color: #d32f2f; font-weight: 600; margin-bottom: 15px;">
                ⚠️ This will immediately stop ALL irrigation activities in ALL rooms.
            </p>
            <p>Are you sure you want to perform an emergency stop?</p>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Emergency Stop',
                class: 'btn-danger',
                onClick: () => this.performEmergencyStop()
            }
        ];

        this.showModal('Emergency Stop Confirmation', content, buttons);
    }

    async performEmergencyStop() {
        try {
            await this.hass.callService('irrigation_addon', 'emergency_stop_all', {});

            this.hideModal();
            this.showToast('Emergency stop executed successfully', 'warning');
            
            // Refresh dashboard
            setTimeout(() => this.renderDashboard(), 1000);
            
        } catch (error) {
            console.error('Failed to perform emergency stop:', error);
            this.showToast('Failed to perform emergency stop: ' + error.message, 'error');
        }
    }

    // Event Management Interface
    renderEvents() {
        const container = document.getElementById('events-container');
        
        if (Object.keys(this.rooms).length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="icon">📅</span>
                    <h3>No Rooms Available</h3>
                    <p>Add rooms first to create irrigation events.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '';

        // Create room tabs for event management
        const roomTabs = document.createElement('div');
        roomTabs.className = 'room-tabs';
        
        const tabButtons = document.createElement('div');
        tabButtons.className = 'tab-buttons';
        
        const tabContents = document.createElement('div');
        tabContents.className = 'tab-contents';

        let firstRoom = true;
        Object.entries(this.rooms).forEach(([roomId, room]) => {
            // Tab button
            const tabBtn = document.createElement('button');
            tabBtn.className = `tab-btn ${firstRoom ? 'active' : ''}`;
            tabBtn.dataset.roomId = roomId;
            tabBtn.innerHTML = `
                <span class="icon">🏠</span>
                ${this.escapeHtml(room.name)}
                <span class="event-count">${room.events ? room.events.length : 0}</span>
            `;
            tabButtons.appendChild(tabBtn);

            // Tab content
            const tabContent = document.createElement('div');
            tabContent.className = `tab-content ${firstRoom ? 'active' : ''}`;
            tabContent.dataset.roomId = roomId;
            tabContent.innerHTML = this.renderRoomEvents(roomId, room);
            tabContents.appendChild(tabContent);

            firstRoom = false;
        });

        roomTabs.appendChild(tabButtons);
        roomTabs.appendChild(tabContents);
        container.appendChild(roomTabs);

        // Set up tab switching
        this.setupEventTabListeners();
    }

    renderHistory() {
        const container = document.getElementById('history-container');
        container.innerHTML = '<p>History view will be implemented in a future task</p>';
    }

    renderSettings() {
        const container = document.getElementById('settings-container');
        container.innerHTML = '<p>Settings view will be implemented in a future task</p>';
    }

    showAddRoomModal() {
        this.showToast('Room management will be implemented in the config flow', 'info');
    }

    showEditRoomModal(roomId) {
        this.showToast('Room editing will be implemented in the config flow', 'info');
    }

    // Event Management Modals
    showAddEventModal(roomId) {
        const room = this.rooms[roomId];
        if (!room) return;

        // Check which event types are available
        const existingTypes = (room.events || []).map(e => e.event_type);
        const availableTypes = ['P1', 'P2'].filter(type => !existingTypes.includes(type));

        if (availableTypes.length === 0) {
            this.showToast('All event types (P1, P2) are already configured for this room', 'warning');
            return;
        }

        const content = `
            <div class="form-group">
                <label class="form-label">Room: ${this.escapeHtml(room.name)}</label>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="event-type">Event Type</label>
                <select id="event-type" class="form-select">
                    ${availableTypes.map(type => `<option value="${type}">${type} Event</option>`).join('')}
                </select>
            </div>

            <div class="form-group">
                <label class="form-label" for="event-schedule">Schedule (Cron Expression)</label>
                <select id="event-schedule-preset" class="form-select">
                    <option value="">Select a preset...</option>
                    <option value="0 8 * * *">Daily at 8:00 AM</option>
                    <option value="0 20 * * *">Daily at 8:00 PM</option>
                    <option value="0 8,20 * * *">Daily at 8:00 AM and 8:00 PM</option>
                    <option value="0 */6 * * *">Every 6 hours</option>
                    <option value="0 */4 * * *">Every 4 hours</option>
                    <option value="custom">Custom...</option>
                </select>
                <input type="text" id="event-schedule" class="form-input" 
                       placeholder="0 8,20 * * *" style="margin-top: 10px; display: none;">
                <small style="color: #666; margin-top: 5px; display: block;">
                    Format: minute hour day month weekday (e.g., "0 8,20 * * *" for 8 AM and 8 PM daily)
                </small>
            </div>

            <div class="form-group">
                <label class="form-label">
                    <input type="checkbox" id="event-enabled" checked style="margin-right: 8px;">
                    Enable event immediately
                </label>
            </div>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Create Event',
                class: 'btn-primary',
                onClick: () => this.createEvent(roomId)
            }
        ];

        this.showModal('Add Irrigation Event', content, buttons);

        // Set up schedule preset handling
        document.getElementById('event-schedule-preset').addEventListener('change', (e) => {
            const scheduleInput = document.getElementById('event-schedule');
            if (e.target.value === 'custom') {
                scheduleInput.style.display = 'block';
                scheduleInput.focus();
            } else if (e.target.value) {
                scheduleInput.style.display = 'none';
                scheduleInput.value = e.target.value;
            } else {
                scheduleInput.style.display = 'none';
                scheduleInput.value = '';
            }
        });
    }

    async createEvent(roomId) {
        const eventType = document.getElementById('event-type').value;
        const schedulePreset = document.getElementById('event-schedule-preset').value;
        const schedule = schedulePreset === 'custom' ? 
            document.getElementById('event-schedule').value : 
            (schedulePreset || document.getElementById('event-schedule').value);
        const enabled = document.getElementById('event-enabled').checked;

        if (!eventType) {
            this.showToast('Please select an event type', 'error');
            return;
        }

        if (!schedule) {
            this.showToast('Please provide a schedule', 'error');
            return;
        }

        try {
            await this.hass.callService('irrigation_addon', 'add_event', {
                room_id: roomId,
                event_type: eventType,
                schedule: schedule,
                enabled: enabled,
                shots: [{ duration: 30, interval_after: 0 }] // Default shot
            });

            this.hideModal();
            this.showToast(`${eventType} event created successfully`, 'success');
            
            // Refresh events view
            setTimeout(() => this.renderEvents(), 1000);
            
        } catch (error) {
            console.error('Failed to create event:', error);
            this.showToast('Failed to create event: ' + error.message, 'error');
        }
    }

    showAddShotModal(roomId, eventType) {
        const content = `
            <div class="form-group">
                <label class="form-label">Event: ${eventType}</label>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="shot-duration">Shot Duration</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="number" id="shot-duration-minutes" class="form-input" 
                           min="0" max="60" value="0" placeholder="Minutes" style="flex: 1;">
                    <span>:</span>
                    <input type="number" id="shot-duration-seconds" class="form-input" 
                           min="1" max="59" value="30" placeholder="Seconds" style="flex: 1;">
                </div>
            </div>

            <div class="form-group">
                <label class="form-label" for="shot-interval">Interval After Shot</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="number" id="shot-interval-minutes" class="form-input" 
                           min="0" max="60" value="5" placeholder="Minutes" style="flex: 1;">
                    <span>:</span>
                    <input type="number" id="shot-interval-seconds" class="form-input" 
                           min="0" max="59" value="0" placeholder="Seconds" style="flex: 1;">
                </div>
                <small style="color: #666; margin-top: 5px; display: block;">
                    Time to wait before the next shot (0 for no interval)
                </small>
            </div>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Add Shot',
                class: 'btn-primary',
                onClick: () => this.addShot(roomId, eventType)
            }
        ];

        this.showModal('Add Shot', content, buttons);
    }

    async addShot(roomId, eventType) {
        const durationMinutes = parseInt(document.getElementById('shot-duration-minutes').value) || 0;
        const durationSeconds = parseInt(document.getElementById('shot-duration-seconds').value) || 0;
        const intervalMinutes = parseInt(document.getElementById('shot-interval-minutes').value) || 0;
        const intervalSeconds = parseInt(document.getElementById('shot-interval-seconds').value) || 0;

        const duration = durationMinutes * 60 + durationSeconds;
        const interval = intervalMinutes * 60 + intervalSeconds;

        if (duration < 1) {
            this.showToast('Shot duration must be at least 1 second', 'error');
            return;
        }

        if (duration > 3600) {
            this.showToast('Shot duration cannot exceed 1 hour', 'error');
            return;
        }

        try {
            await this.hass.callService('irrigation_addon', 'add_shot', {
                room_id: roomId,
                event_type: eventType,
                duration: duration,
                interval_after: interval
            });

            this.hideModal();
            this.showToast('Shot added successfully', 'success');
            
            // Refresh events view
            setTimeout(() => this.renderEvents(), 1000);
            
        } catch (error) {
            console.error('Failed to add shot:', error);
            this.showToast('Failed to add shot: ' + error.message, 'error');
        }
    }

    async toggleEvent(roomId, eventType) {
        try {
            const room = this.rooms[roomId];
            const event = room.events.find(e => e.event_type === eventType);
            const newState = !event.enabled;

            await this.hass.callService('irrigation_addon', 'toggle_event', {
                room_id: roomId,
                event_type: eventType,
                enabled: newState
            });

            this.showToast(`Event ${newState ? 'enabled' : 'disabled'} successfully`, 'success');
            
            // Refresh events view
            setTimeout(() => this.renderEvents(), 1000);
            
        } catch (error) {
            console.error('Failed to toggle event:', error);
            this.showToast('Failed to toggle event: ' + error.message, 'error');
        }
    }

    showDeleteEventConfirmation(roomId, eventType) {
        const room = this.rooms[roomId];
        const event = room.events.find(e => e.event_type === eventType);
        
        const content = `
            <p>Are you sure you want to delete the <strong>${eventType}</strong> event for <strong>${this.escapeHtml(room.name)}</strong>?</p>
            <p style="color: #d32f2f;">This will permanently remove the event and all its shots. This action cannot be undone.</p>
            <div style="background: #f8f9fa; padding: 10px; border-radius: 6px; margin-top: 15px;">
                <strong>Event Details:</strong><br>
                • ${event.shots ? event.shots.length : 0} shots<br>
                • ${this.formatDuration(this.calculateEventDuration(event))} total duration<br>
                • ${event.enabled ? 'Currently enabled' : 'Currently disabled'}
            </div>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Delete Event',
                class: 'btn-danger',
                onClick: () => {
                    this.deleteEvent(roomId, eventType);
                    this.hideModal();
                }
            }
        ];

        this.showModal('Delete Event Confirmation', content, buttons);
    }

    async deleteEvent(roomId, eventType) {
        try {
            await this.hass.callService('irrigation_addon', 'delete_event', {
                room_id: roomId,
                event_type: eventType
            });

            this.showToast('Event deleted successfully', 'success');
            
            // Refresh events view
            setTimeout(() => this.renderEvents(), 1000);
            
        } catch (error) {
            console.error('Failed to delete event:', error);
            this.showToast('Failed to delete event: ' + error.message, 'error');
        }
    }

    // Shot drag and drop functionality
    setupShotDragAndDrop() {
        document.querySelectorAll('.shot-item').forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({
                    roomId: item.closest('.shots-list').dataset.roomId,
                    eventType: item.closest('.shots-list').dataset.eventType,
                    shotIndex: parseInt(item.dataset.shotIndex)
                }));
                item.classList.add('dragging');
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
            });
        });

        document.querySelectorAll('.shots-list').forEach(list => {
            list.addEventListener('dragover', (e) => {
                e.preventDefault();
                const dragging = list.querySelector('.dragging');
                const afterElement = this.getDragAfterElement(list, e.clientY);
                
                if (afterElement == null) {
                    list.appendChild(dragging);
                } else {
                    list.insertBefore(dragging, afterElement);
                }
            });

            list.addEventListener('drop', (e) => {
                e.preventDefault();
                const dragData = JSON.parse(e.dataTransfer.getData('text/plain'));
                this.reorderShots(dragData.roomId, dragData.eventType, list);
            });
        });
    }

    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.shot-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    async reorderShots(roomId, eventType, shotsList) {
        try {
            const shotItems = shotsList.querySelectorAll('.shot-item');
            const newOrder = Array.from(shotItems).map(item => parseInt(item.dataset.shotIndex));
            
            await this.hass.callService('irrigation_addon', 'reorder_shots', {
                room_id: roomId,
                event_type: eventType,
                new_order: newOrder
            });

            this.showToast('Shots reordered successfully', 'success');
            
            // Refresh events view
            setTimeout(() => this.renderEvents(), 1000);
            
        } catch (error) {
            console.error('Failed to reorder shots:', error);
            this.showToast('Failed to reorder shots: ' + error.message, 'error');
        }
    }

    showDeleteShotConfirmation(roomId, eventType, shotIndex) {
        const room = this.rooms[roomId];
        const event = room.events.find(e => e.event_type === eventType);
        const shot = event.shots[shotIndex];
        
        const content = `
            <p>Are you sure you want to delete Shot ${shotIndex + 1} from the <strong>${eventType}</strong> event?</p>
            <div style="background: #f8f9fa; padding: 10px; border-radius: 6px; margin-top: 15px;">
                <strong>Shot Details:</strong><br>
                • Duration: ${this.formatDuration(shot.duration)}<br>
                • Interval: ${shot.interval_after > 0 ? this.formatDuration(shot.interval_after) : 'None'}
            </div>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Delete Shot',
                class: 'btn-danger',
                onClick: () => {
                    this.deleteShot(roomId, eventType, shotIndex);
                    this.hideModal();
                }
            }
        ];

        this.showModal('Delete Shot Confirmation', content, buttons);
    }

    async deleteShot(roomId, eventType, shotIndex) {
        try {
            await this.hass.callService('irrigation_addon', 'delete_shot', {
                room_id: roomId,
                event_type: eventType,
                shot_index: shotIndex
            });

            this.showToast('Shot deleted successfully', 'success');
            
            // Refresh events view
            setTimeout(() => this.renderEvents(), 1000);
            
        } catch (error) {
            console.error('Failed to delete shot:', error);
            this.showToast('Failed to delete shot: ' + error.message, 'error');
        }
    }

    // Utility Functions
    showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        toast.innerHTML = `
            <div class="toast-title">${this.getToastTitle(type)}</div>
            <div class="toast-message">${this.escapeHtml(message)}</div>
        `;

        container.appendChild(toast);

        // Auto remove after duration
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, duration);

        // Click to dismiss
        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        });
    }

    getToastTitle(type) {
        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Information'
        };
        return titles[type] || 'Notification';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatDateTime(dateString) {
        if (!dateString) return null;
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (error) {
            return null;
        }
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
        }
    }

    // Real-time progress tracking
    startRoomProgressTracking(roomId) {
        // Clear any existing interval for this room
        if (this.progressIntervals && this.progressIntervals[roomId]) {
            clearInterval(this.progressIntervals[roomId]);
        }

        if (!this.progressIntervals) {
            this.progressIntervals = {};
        }

        // Update progress every second
        this.progressIntervals[roomId] = setInterval(() => {
            this.updateRoomProgress(roomId);
        }, 1000);
    }

    stopRoomProgressTracking(roomId) {
        if (this.progressIntervals && this.progressIntervals[roomId]) {
            clearInterval(this.progressIntervals[roomId]);
            delete this.progressIntervals[roomId];
        }
    }

    updateRoomProgress(roomId) {
        const card = document.querySelector(`[data-room-id="${roomId}"]`);
        if (!card) return;

        const status = this.getRoomStatus(roomId);
        
        // If no active irrigation, stop tracking
        if (!status.active_irrigation && !status.manual_run) {
            this.stopRoomProgressTracking(roomId);
            this.renderDashboard(); // Refresh to remove progress bar
            return;
        }

        // Update progress bar
        const progressContainer = card.querySelector('.progress-container');
        if (progressContainer) {
            const newProgressHtml = this.renderProgressBar(status);
            progressContainer.outerHTML = newProgressHtml;
            
            // Re-attach event listeners for the new progress bar
            this.setupRoomCardEventListeners(card, roomId);
        }
    }

    // Enhanced stop confirmation
    showStopConfirmation(roomId) {
        const room = this.rooms[roomId];
        const status = this.getRoomStatus(roomId);
        
        if (!status.active_irrigation && !status.manual_run) {
            this.showToast('No active irrigation to stop', 'info');
            return;
        }

        let irrigationType = '';
        let details = '';
        
        if (status.active_irrigation_details) {
            irrigationType = `${status.active_irrigation_details.event_type} Event`;
            details = `Shot ${status.active_irrigation_details.current_shot + 1}/${status.active_irrigation_details.total_shots}`;
        } else if (status.manual_run_details) {
            irrigationType = 'Manual Run';
            const remaining = Math.max(0, status.manual_run_details.remaining);
            details = `${this.formatDuration(remaining)} remaining`;
        }

        const content = `
            <div style="margin-bottom: 15px;">
                <strong>Room:</strong> ${this.escapeHtml(room.name)}<br>
                <strong>Type:</strong> ${irrigationType}<br>
                <strong>Status:</strong> ${details}
            </div>
            <p>Are you sure you want to stop the current irrigation?</p>
            <p style="color: #666; font-size: 0.9rem;">This will immediately turn off the pump and all zones.</p>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Stop Irrigation',
                class: 'btn-warning',
                onClick: () => {
                    this.stopIrrigation(roomId);
                    this.hideModal();
                }
            }
        ];

        this.showModal('Stop Irrigation Confirmation', content, buttons);
    }

    // Emergency stop for specific room
    showEmergencyStopRoomConfirmation(roomId) {
        const room = this.rooms[roomId];
        
        const content = `
            <p style="color: #d32f2f; font-weight: 600; margin-bottom: 15px;">
                ⚠️ Emergency stop will immediately shut off all irrigation equipment for this room.
            </p>
            <p><strong>Room:</strong> ${this.escapeHtml(room.name)}</p>
            <p>This action cannot be undone. Are you sure?</p>
        `;

        const buttons = [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                onClick: () => this.hideModal()
            },
            {
                text: 'Emergency Stop',
                class: 'btn-danger',
                onClick: () => {
                    this.performEmergencyStopRoom(roomId);
                    this.hideModal();
                }
            }
        ];

        this.showModal('Emergency Stop Room', content, buttons);
    }

    async performEmergencyStopRoom(roomId) {
        try {
            await this.hass.callService('irrigation_addon', 'emergency_stop_room', {
                room_id: roomId
            });

            this.showToast('Emergency stop executed for room', 'warning');
            this.stopRoomProgressTracking(roomId);
            
            // Refresh dashboard
            setTimeout(() => this.renderDashboard(), 1000);
            
        } catch (error) {
            console.error('Failed to perform emergency stop for room:', error);
            this.showToast('Failed to perform emergency stop: ' + error.message, 'error');
        }
    }

    // Enhanced irrigation status display
    renderLastEventInfo(roomId) {
        const status = this.getRoomStatus(roomId);
        const lastEvents = status.last_events || {};
        
        return Object.entries(lastEvents)
            .filter(([_, timestamp]) => timestamp)
            .map(([eventType, timestamp]) => {
                const timeAgo = this.getTimeAgo(timestamp);
                return `
                    <div class="last-event-item">
                        <span class="event-type">${eventType}</span>
                        <span class="event-time">${timeAgo}</span>
                    </div>
                `;
            }).join('') || '<div class="no-events">No recent events</div>';
    }

    getTimeAgo(timestamp) {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            return date.toLocaleDateString();
        } catch (error) {
            return 'Unknown';
        }
    }

    // Event Management Methods
    renderRoomEvents(roomId, room) {
        const events = room.events || [];
        
        return `
            <div class="room-events-header">
                <h3>${this.escapeHtml(room.name)} - Irrigation Events</h3>
                <button class="btn btn-primary add-event-btn" data-room-id="${roomId}">
                    <span class="icon">➕</span>
                    Add Event
                </button>
            </div>
            
            <div class="events-grid">
                ${events.length > 0 ? events.map(event => this.renderEventCard(roomId, event)).join('') : this.renderNoEventsMessage()}
            </div>
        `;
    }

    renderEventCard(roomId, event) {
        const totalDuration = this.calculateEventDuration(event);
        const shotCount = event.shots ? event.shots.length : 0;
        const nextRun = event.next_run ? this.formatDateTime(event.next_run) : 'Not scheduled';
        const lastRun = event.last_run ? this.formatDateTime(event.last_run) : 'Never';

        return `
            <div class="event-card ${event.enabled ? 'enabled' : 'disabled'}" data-room-id="${roomId}" data-event-type="${event.event_type}">
                <div class="event-header">
                    <div class="event-title">
                        <span class="event-type-badge ${event.event_type.toLowerCase()}">${event.event_type}</span>
                        <span class="event-status ${event.enabled ? 'enabled' : 'disabled'}">
                            ${event.enabled ? '✓ Enabled' : '✗ Disabled'}
                        </span>
                    </div>
                    <div class="event-actions">
                        <button class="btn btn-sm btn-secondary edit-event-btn" data-room-id="${roomId}" data-event-type="${event.event_type}">
                            <span class="icon">✏️</span>
                        </button>
                        <button class="btn btn-sm ${event.enabled ? 'btn-warning' : 'btn-success'} toggle-event-btn" 
                                data-room-id="${roomId}" data-event-type="${event.event_type}">
                            <span class="icon">${event.enabled ? '⏸️' : '▶️'}</span>
                        </button>
                        <button class="btn btn-sm btn-danger delete-event-btn" data-room-id="${roomId}" data-event-type="${event.event_type}">
                            <span class="icon">🗑️</span>
                        </button>
                    </div>
                </div>

                <div class="event-details">
                    <div class="event-info-grid">
                        <div class="info-item">
                            <span class="info-label">Schedule</span>
                            <span class="info-value">${this.formatCronExpression(event.schedule)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Shots</span>
                            <span class="info-value">${shotCount} shots</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Duration</span>
                            <span class="info-value">${this.formatDuration(totalDuration)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Next Run</span>
                            <span class="info-value">${nextRun}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Last Run</span>
                            <span class="info-value">${lastRun}</span>
                        </div>
                    </div>
                </div>

                <div class="shots-container">
                    <div class="shots-header">
                        <h4>Shots (${shotCount})</h4>
                        <button class="btn btn-sm btn-primary add-shot-btn" data-room-id="${roomId}" data-event-type="${event.event_type}">
                            <span class="icon">➕</span>
                            Add Shot
                        </button>
                    </div>
                    <div class="shots-list" data-room-id="${roomId}" data-event-type="${event.event_type}">
                        ${event.shots ? event.shots.map((shot, index) => this.renderShotItem(roomId, event.event_type, shot, index)).join('') : ''}
                    </div>
                </div>
            </div>
        `;
    }

    renderShotItem(roomId, eventType, shot, index) {
        return `
            <div class="shot-item" data-shot-index="${index}" draggable="true">
                <div class="shot-handle">
                    <span class="icon">⋮⋮</span>
                </div>
                <div class="shot-info">
                    <div class="shot-number">Shot ${index + 1}</div>
                    <div class="shot-details">
                        <span class="shot-duration">${this.formatDuration(shot.duration)}</span>
                        ${shot.interval_after > 0 ? `<span class="shot-interval">+ ${this.formatDuration(shot.interval_after)} wait</span>` : ''}
                    </div>
                </div>
                <div class="shot-actions">
                    <button class="btn btn-sm btn-secondary edit-shot-btn" 
                            data-room-id="${roomId}" data-event-type="${eventType}" data-shot-index="${index}">
                        <span class="icon">✏️</span>
                    </button>
                    <button class="btn btn-sm btn-danger delete-shot-btn" 
                            data-room-id="${roomId}" data-event-type="${eventType}" data-shot-index="${index}">
                        <span class="icon">🗑️</span>
                    </button>
                </div>
            </div>
        `;
    }

    renderNoEventsMessage() {
        return `
            <div class="no-events-message">
                <span class="icon">📅</span>
                <h4>No Events Configured</h4>
                <p>Create P1 and P2 irrigation events to automate watering schedules.</p>
            </div>
        `;
    }

    setupEventTabListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                this.switchEventTab(roomId);
            });
        });

        // Event management buttons
        this.setupEventManagementListeners();
    }

    setupEventManagementListeners() {
        // Add event buttons
        document.querySelectorAll('.add-event-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                this.showAddEventModal(roomId);
            });
        });

        // Edit event buttons
        document.querySelectorAll('.edit-event-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                const eventType = e.currentTarget.dataset.eventType;
                this.showEditEventModal(roomId, eventType);
            });
        });

        // Toggle event buttons
        document.querySelectorAll('.toggle-event-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                const eventType = e.currentTarget.dataset.eventType;
                this.toggleEvent(roomId, eventType);
            });
        });

        // Delete event buttons
        document.querySelectorAll('.delete-event-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                const eventType = e.currentTarget.dataset.eventType;
                this.showDeleteEventConfirmation(roomId, eventType);
            });
        });

        // Shot management buttons
        document.querySelectorAll('.add-shot-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                const eventType = e.currentTarget.dataset.eventType;
                this.showAddShotModal(roomId, eventType);
            });
        });

        document.querySelectorAll('.edit-shot-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                const eventType = e.currentTarget.dataset.eventType;
                const shotIndex = parseInt(e.currentTarget.dataset.shotIndex);
                this.showEditShotModal(roomId, eventType, shotIndex);
            });
        });

        document.querySelectorAll('.delete-shot-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const roomId = e.currentTarget.dataset.roomId;
                const eventType = e.currentTarget.dataset.eventType;
                const shotIndex = parseInt(e.currentTarget.dataset.shotIndex);
                this.showDeleteShotConfirmation(roomId, eventType, shotIndex);
            });
        });

        // Set up drag and drop for shot reordering
        this.setupShotDragAndDrop();
    }

    switchEventTab(roomId) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-room-id="${roomId}"].tab-btn`).classList.add('active');

        // Update tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.querySelector(`[data-room-id="${roomId}"].tab-content`).classList.add('active');
    }

    calculateEventDuration(event) {
        if (!event.shots || event.shots.length === 0) return 0;
        
        let total = 0;
        event.shots.forEach((shot, index) => {
            total += shot.duration;
            if (index < event.shots.length - 1) { // Don't add interval after last shot
                total += shot.interval_after || 0;
            }
        });
        return total;
    }

    formatCronExpression(cron) {
        if (!cron) return 'Not scheduled';
        
        // Basic cron expression formatting
        const parts = cron.split(' ');
        if (parts.length !== 5) return cron;
        
        const [minute, hour, day, month, weekday] = parts;
        
        // Handle common patterns
        if (cron === '0 8,20 * * *') return 'Daily at 8:00 AM and 8:00 PM';
        if (cron === '0 8 * * *') return 'Daily at 8:00 AM';
        if (cron === '0 20 * * *') return 'Daily at 8:00 PM';
        if (cron === '0 */6 * * *') return 'Every 6 hours';
        if (cron === '0 */4 * * *') return 'Every 4 hours';
        
        return cron; // Fallback to raw cron expression
    }

    // Settings Management Methods
    
    renderSettings() {
        const container = document.getElementById('settings-container');
        
        container.innerHTML = `
            <div class="settings-content">
                <div class="settings-section">
                    <h3 class="section-title">
                        <span class="icon">⚙️</span>
                        Irrigation Settings
                    </h3>
                    <div class="settings-grid">
                        <div class="setting-item">
                            <label for="pump-zone-delay" class="setting-label">
                                Pump to Zone Delay
                                <span class="setting-description">Delay in seconds between pump activation and zone activation</span>
                            </label>
                            <div class="setting-input-group">
                                <input type="number" 
                                       id="pump-zone-delay" 
                                       class="setting-input" 
                                       min="0" 
                                       max="60" 
                                       value="${this.settings.pump_zone_delay || 3}">
                                <span class="input-suffix">seconds</span>
                            </div>
                        </div>

                        <div class="setting-item">
                            <label for="sensor-update-interval" class="setting-label">
                                Sensor Update Interval
                                <span class="setting-description">How often to update sensor readings</span>
                            </label>
                            <div class="setting-input-group">
                                <input type="number" 
                                       id="sensor-update-interval" 
                                       class="setting-input" 
                                       min="5" 
                                       max="300" 
                                       value="${this.settings.sensor_update_interval || 30}">
                                <span class="input-suffix">seconds</span>
                            </div>
                        </div>

                        <div class="setting-item">
                            <label for="default-manual-duration" class="setting-label">
                                Default Manual Run Duration
                                <span class="setting-description">Default duration for manual irrigation runs</span>
                            </label>
                            <div class="setting-input-group">
                                <input type="number" 
                                       id="default-manual-duration" 
                                       class="setting-input" 
                                       min="30" 
                                       max="3600" 
                                       value="${this.settings.default_manual_duration || 300}">
                                <span class="input-suffix">seconds</span>
                            </div>
                        </div>

                        <div class="setting-item">
                            <label for="max-daily-irrigation" class="setting-label">
                                Maximum Daily Irrigation
                                <span class="setting-description">Maximum total irrigation time per room per day</span>
                            </label>
                            <div class="setting-input-group">
                                <input type="number" 
                                       id="max-daily-irrigation" 
                                       class="setting-input" 
                                       min="300" 
                                       max="7200" 
                                       value="${this.settings.max_daily_irrigation || 3600}">
                                <span class="input-suffix">seconds</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3 class="section-title">
                        <span class="icon">🛡️</span>
                        Safety & Fail-Safe Settings
                    </h3>
                    <div class="settings-grid">
                        <div class="setting-item">
                            <label class="setting-label checkbox-label">
                                <input type="checkbox" 
                                       id="fail-safe-enabled" 
                                       class="setting-checkbox" 
                                       ${this.settings.fail_safe_enabled !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                Enable Fail-Safe Mechanisms
                                <span class="setting-description">Enable safety checks before irrigation (light schedule, entity availability, etc.)</span>
                            </label>
                        </div>

                        <div class="setting-item">
                            <label class="setting-label checkbox-label">
                                <input type="checkbox" 
                                       id="emergency-stop-enabled" 
                                       class="setting-checkbox" 
                                       ${this.settings.emergency_stop_enabled !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                Enable Emergency Stop
                                <span class="setting-description">Allow emergency stop functionality for all irrigation activities</span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3 class="section-title">
                        <span class="icon">🔔</span>
                        Notification Settings
                    </h3>
                    <div class="settings-grid">
                        <div class="setting-item">
                            <label class="setting-label checkbox-label">
                                <input type="checkbox" 
                                       id="notifications-enabled" 
                                       class="setting-checkbox" 
                                       ${this.settings.notifications_enabled !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                Enable Notifications
                                <span class="setting-description">Show toast notifications for irrigation events</span>
                            </label>
                        </div>

                        <div class="setting-item">
                            <label class="setting-label checkbox-label">
                                <input type="checkbox" 
                                       id="error-notifications" 
                                       class="setting-checkbox" 
                                       ${this.settings.error_notifications !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                Error Notifications
                                <span class="setting-description">Show notifications for irrigation errors and failures</span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3 class="section-title">
                        <span class="icon">📊</span>
                        Logging & Diagnostics
                    </h3>
                    <div class="settings-grid">
                        <div class="setting-item">
                            <label for="logging-level" class="setting-label">
                                Logging Level
                                <span class="setting-description">Level of detail for system logs</span>
                            </label>
                            <select id="logging-level" class="setting-select">
                                <option value="ERROR" ${this.settings.logging_level === 'ERROR' ? 'selected' : ''}>Error</option>
                                <option value="WARNING" ${this.settings.logging_level === 'WARNING' ? 'selected' : ''}>Warning</option>
                                <option value="INFO" ${this.settings.logging_level === 'INFO' || !this.settings.logging_level ? 'selected' : ''}>Info</option>
                                <option value="DEBUG" ${this.settings.logging_level === 'DEBUG' ? 'selected' : ''}>Debug</option>
                            </select>
                        </div>

                        <div class="setting-item">
                            <label for="history-retention" class="setting-label">
                                History Retention
                                <span class="setting-description">How long to keep irrigation history</span>
                            </label>
                            <select id="history-retention" class="setting-select">
                                <option value="7" ${this.settings.max_history_days === 7 ? 'selected' : ''}>7 days</option>
                                <option value="14" ${this.settings.max_history_days === 14 ? 'selected' : ''}>14 days</option>
                                <option value="30" ${this.settings.max_history_days === 30 || !this.settings.max_history_days ? 'selected' : ''}>30 days</option>
                                <option value="60" ${this.settings.max_history_days === 60 ? 'selected' : ''}>60 days</option>
                                <option value="90" ${this.settings.max_history_days === 90 ? 'selected' : ''}>90 days</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3 class="section-title">
                        <span class="icon">💾</span>
                        Backup & Restore
                    </h3>
                    <div class="backup-controls">
                        <div class="backup-actions">
                            <button id="create-backup-btn" class="btn btn-secondary">
                                <span class="icon">📦</span>
                                Create Backup
                            </button>
                            <button id="restore-backup-btn" class="btn btn-secondary">
                                <span class="icon">📥</span>
                                Restore Backup
                            </button>
                            <button id="export-settings-btn" class="btn btn-secondary">
                                <span class="icon">📤</span>
                                Export Settings
                            </button>
                        </div>
                        <div class="backup-info">
                            <p class="backup-description">
                                Create backups of your irrigation configuration including rooms, events, and settings. 
                                Backups can be restored later or transferred to another system.
                            </p>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3 class="section-title">
                        <span class="icon">🔧</span>
                        System Information
                    </h3>
                    <div class="system-info">
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="info-label">Total Rooms</span>
                                <span class="info-value">${Object.keys(this.rooms).length}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Active Irrigations</span>
                                <span class="info-value" id="active-irrigations-count">0</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">System Status</span>
                                <span class="info-value status-healthy">Healthy</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Last Updated</span>
                                <span class="info-value">${new Date().toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Set up event listeners for settings
        this.setupSettingsEventListeners();
    }

    setupSettingsEventListeners() {
        // Save settings button
        const saveBtn = document.getElementById('save-settings-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveSettings();
            });
        }

        // Backup and restore buttons
        const createBackupBtn = document.getElementById('create-backup-btn');
        if (createBackupBtn) {
            createBackupBtn.addEventListener('click', () => {
                this.createBackup();
            });
        }

        const restoreBackupBtn = document.getElementById('restore-backup-btn');
        if (restoreBackupBtn) {
            restoreBackupBtn.addEventListener('click', () => {
                this.showRestoreBackupModal();
            });
        }

        const exportSettingsBtn = document.getElementById('export-settings-btn');
        if (exportSettingsBtn) {
            exportSettingsBtn.addEventListener('click', () => {
                this.exportSettings();
            });
        }

        // Add input validation
        this.setupSettingsValidation();
    }

    setupSettingsValidation() {
        // Pump zone delay validation
        const pumpDelayInput = document.getElementById('pump-zone-delay');
        if (pumpDelayInput) {
            pumpDelayInput.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                if (value < 0) e.target.value = 0;
                if (value > 60) e.target.value = 60;
            });
        }

        // Sensor update interval validation
        const sensorIntervalInput = document.getElementById('sensor-update-interval');
        if (sensorIntervalInput) {
            sensorIntervalInput.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                if (value < 5) e.target.value = 5;
                if (value > 300) e.target.value = 300;
            });
        }

        // Manual duration validation
        const manualDurationInput = document.getElementById('default-manual-duration');
        if (manualDurationInput) {
            manualDurationInput.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                if (value < 30) e.target.value = 30;
                if (value > 3600) e.target.value = 3600;
            });
        }

        // Max daily irrigation validation
        const maxDailyInput = document.getElementById('max-daily-irrigation');
        if (maxDailyInput) {
            maxDailyInput.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                if (value < 300) e.target.value = 300;
                if (value > 7200) e.target.value = 7200;
            });
        }
    }

    async saveSettings() {
        try {
            // Show loading state
            const saveBtn = document.getElementById('save-settings-btn');
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<span class="icon">⏳</span> Saving...';
            saveBtn.disabled = true;

            // Collect settings from form
            const newSettings = {
                pump_zone_delay: parseInt(document.getElementById('pump-zone-delay').value),
                sensor_update_interval: parseInt(document.getElementById('sensor-update-interval').value),
                default_manual_duration: parseInt(document.getElementById('default-manual-duration').value),
                max_daily_irrigation: parseInt(document.getElementById('max-daily-irrigation').value),
                fail_safe_enabled: document.getElementById('fail-safe-enabled').checked,
                emergency_stop_enabled: document.getElementById('emergency-stop-enabled').checked,
                notifications_enabled: document.getElementById('notifications-enabled').checked,
                error_notifications: document.getElementById('error-notifications').checked,
                logging_level: document.getElementById('logging-level').value,
                max_history_days: parseInt(document.getElementById('history-retention').value)
            };

            // Call Home Assistant service to update settings
            await this.hass.callService('irrigation_addon', 'update_settings', {
                settings: newSettings
            });

            // Update local settings
            this.settings = { ...this.settings, ...newSettings };

            // Show success message
            this.showToast('Settings saved successfully', 'success');

            // Restore button state
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;

        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showToast('Failed to save settings: ' + error.message, 'error');

            // Restore button state
            const saveBtn = document.getElementById('save-settings-btn');
            saveBtn.innerHTML = '<span class="icon">💾</span> Save Settings';
            saveBtn.disabled = false;
        }
    }

    async createBackup() {
        try {
            // Show loading state
            const backupBtn = document.getElementById('create-backup-btn');
            const originalText = backupBtn.innerHTML;
            backupBtn.innerHTML = '<span class="icon">⏳</span> Creating...';
            backupBtn.disabled = true;

            // Call Home Assistant service to create backup
            const response = await this.hass.callService('irrigation_addon', 'create_backup', {});

            if (response && response.backup_data) {
                // Download backup file
                const backupData = JSON.stringify(response.backup_data, null, 2);
                const blob = new Blob([backupData], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = `irrigation_backup_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                this.showToast('Backup created and downloaded successfully', 'success');
            } else {
                throw new Error('Invalid backup response');
            }

            // Restore button state
            backupBtn.innerHTML = originalText;
            backupBtn.disabled = false;

        } catch (error) {
            console.error('Failed to create backup:', error);
            this.showToast('Failed to create backup: ' + error.message, 'error');

            // Restore button state
            const backupBtn = document.getElementById('create-backup-btn');
            backupBtn.innerHTML = '<span class="icon">📦</span> Create Backup';
            backupBtn.disabled = false;
        }
    }

    showRestoreBackupModal() {
        this.showModal('Restore Backup', `
            <div class="restore-backup-form">
                <div class="form-group">
                    <label for="backup-file" class="form-label">Select Backup File</label>
                    <input type="file" id="backup-file" class="form-input" accept=".json">
                    <div class="form-help">
                        Select a backup file created by the irrigation system.
                    </div>
                </div>
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="confirm-restore" class="form-checkbox">
                        <span class="checkbox-custom"></span>
                        I understand this will replace all current configuration
                    </label>
                </div>
            </div>
        `, [
            {
                text: 'Cancel',
                class: 'btn-secondary',
                action: () => this.hideModal()
            },
            {
                text: 'Restore',
                class: 'btn-danger',
                action: () => this.restoreBackup()
            }
        ]);
    }

    async restoreBackup() {
        try {
            const fileInput = document.getElementById('backup-file');
            const confirmCheckbox = document.getElementById('confirm-restore');

            if (!fileInput.files[0]) {
                this.showToast('Please select a backup file', 'error');
                return;
            }

            if (!confirmCheckbox.checked) {
                this.showToast('Please confirm you understand this will replace current configuration', 'error');
                return;
            }

            // Read backup file
            const file = fileInput.files[0];
            const backupData = JSON.parse(await file.text());

            // Call Home Assistant service to restore backup
            await this.hass.callService('irrigation_addon', 'restore_backup', {
                backup_data: backupData
            });

            this.hideModal();
            this.showToast('Backup restored successfully. Reloading...', 'success');

            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 2000);

        } catch (error) {
            console.error('Failed to restore backup:', error);
            this.showToast('Failed to restore backup: ' + error.message, 'error');
        }
    }

    async exportSettings() {
        try {
            // Export only settings (not full backup)
            const settingsData = {
                export_timestamp: new Date().toISOString(),
                settings: this.settings
            };

            const blob = new Blob([JSON.stringify(settingsData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `irrigation_settings_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showToast('Settings exported successfully', 'success');

        } catch (error) {
            console.error('Failed to export settings:', error);
            this.showToast('Failed to export settings: ' + error.message, 'error');
        }
    }
}

// Initialize the irrigation panel when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.irrigationPanel = new IrrigationPanel();
});

// Export for potential external use
window.IrrigationPanel = IrrigationPanel;