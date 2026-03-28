// ============================================
// AutomataAI Dashboard - JavaScript (Pro Version)
// ============================================

let dashboard;

class AutomataAIDashboard {
    constructor() {
        this.ws = null;
        this.logs = [];
        this.maxLogs = 100;
        this.token = localStorage.getItem('automata_token');
        this.user = null;
        this.estado = {
            estado_actual: 'DESCANSANDO',
            ingresos_totales: 0,
            modelos_activos: 0,
            modelos_exitosos: 0,
            modelos_fallidos: 0,
            ciclos_completados: 0,
            tasa_exito: 0
        };
        this.modelos = [];
        
        this.init();
    }
    
    async init() {
        if (!this.token) {
            this.renderLogin();
            return;
        }

        const authenticated = await this.verificarToken();
        if (!authenticated) {
            this.renderLogin();
            return;
        }

        this.renderDashboard();
        this.conectarWebSocket();
        this.cargarEstadoInicial();
        this.cargarModelos();
        this.configurarEventos();
    }

    async verificarToken() {
        try {
            const response = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (response.ok) {
                this.user = await response.json();
                return true;
            }
            this.token = null;
            localStorage.removeItem('automata_token');
            return false;
        } catch (e) {
            return false;
        }
    }
    
    renderLogin() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="login-screen">
                <div class="login-card glass-effect">
                    <div class="login-header">
                        <div class="logo-icon">⚙️</div>
                        <h1>AUTOMATA AI</h1>
                        <p>Inicia sesión para acceder al centro de mando</p>
                    </div>
                    <form id="login-form" class="login-form">
                        <div class="form-group">
                            <label>Usuario</label>
                            <input type="text" id="username" placeholder="admin" required autofocus />
                        </div>
                        <div class="form-group">
                            <label>Contraseña</label>
                            <input type="password" id="password" placeholder="••••••••" required />
                        </div>
                        <div id="login-error" class="error-msg" style="display: none;"></div>
                        <button type="submit" class="btn-primary login-btn">ACCEDER AL SISTEMA</button>
                    </form>
                    <div class="login-footer">
                        <span>Fase 3: Ejecución Real</span>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
    }

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('login-error');
        
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch('/api/auth/login', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                localStorage.setItem('automata_token', this.token);
                this.init();
            } else {
                errorDiv.textContent = 'Credenciales inválidas. Intenta de nuevo.';
                errorDiv.style.display = 'block';
            }
        } catch (err) {
            errorDiv.textContent = 'Error de conexión con el servidor.';
            errorDiv.style.display = 'block';
        }
    }

    async apiFetch(url, options = {}) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.token}`
        };

        const response = await fetch(url, options);
        if (response.status === 401) {
            this.logout();
            return null;
        }
        return response;
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('automata_token');
        if (this.ws) this.ws.close();
        this.renderLogin();
    }
    
    renderDashboard() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="dashboard fadeIn">
                <header class="header">
                    <div class="header-left">
                        <h1>⚙️ AUTOMATA AI</h1>
                        <span class="version-tag">PRO v3.0</span>
                    </div>
                    <div class="header-status">
                        <div class="status-badge glass-effect">
                            <div class="status-dot"></div>
                            <span id="status-text">${this.estado.estado_actual}</span>
                        </div>
                        <div class="user-badge" onclick="dashboard.logout()" title="Cerrar sesión">
                            <span>${this.user ? this.user.full_name : 'Admin'}</span>
                            <div class="avatar">A</div>
                        </div>
                    </div>
                </header>
                
                <div class="main-content">
                    <!-- Panel de KPIs -->
                    <div class="kpi-panel">
                        <div class="kpi-card glass-effect animate-up" style="animation-delay: 0.1s">
                            <div class="kpi-icon">💰</div>
                            <div class="kpi-content">
                                <div class="kpi-label">Ingresos Totales (USDT)</div>
                                <div class="kpi-value" id="kpi-ingresos">$0.00</div>
                                <div class="progress-container">
                                    <div class="progress-bar">
                                        <div class="progress-fill" id="progress-ingresos" style="width: 0%"></div>
                                    </div>
                                    <span class="progress-text">Meta: $1,000</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="kpi-card glass-effect animate-up" style="animation-delay: 0.2s">
                            <div class="kpi-icon">🧩</div>
                            <div class="kpi-content">
                                <div class="kpi-label">Modelos Activos</div>
                                <div class="kpi-value" id="kpi-activos">0</div>
                                <div class="kpi-subtext">En ejecución real</div>
                            </div>
                        </div>
                        
                        <div class="kpi-card glass-effect animate-up" style="animation-delay: 0.3s">
                            <div class="kpi-icon">🚀</div>
                            <div class="kpi-content">
                                <div class="kpi-label">Modelos Exitosos</div>
                                <div class="kpi-value" id="kpi-exitosos">0</div>
                                <div class="kpi-subtext">Algoritmos optimizados</div>
                            </div>
                        </div>
                        
                        <div class="kpi-card glass-effect animate-up" style="animation-delay: 0.4s">
                            <div class="kpi-icon">⚖️</div>
                            <div class="kpi-content">
                                <div class="kpi-label">Tasa de Éxito</div>
                                <div class="kpi-value" id="kpi-tasa">0%</div>
                                <div class="kpi-subtext">Ciclos: <span id="ciclos">0</span></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Panel de Logs -->
                    <div class="logs-panel glass-effect animate-up" style="animation-delay: 0.5s">
                        <div class="panel-header">
                            <div class="panel-title">
                                <span class="pulse-icon"></span>
                                📡 PENSAMIENTO EN VIVO
                            </div>
                            <div class="panel-actions">
                                <button class="btn-icon" onclick="dashboard.limpiarLogs()" title="Limpiar logs">🗑️</button>
                            </div>
                        </div>
                        <div class="logs-container" id="logs-container"></div>
                        <div class="control-actions">
                            <button class="btn btn-start" id="btn-iniciar">INICIAR AGENTE</button>
                            <button class="btn btn-pause" id="btn-pausar">PAUSAR</button>
                            <button class="btn btn-config" id="btn-config">⚙️ CONFIGURAR</button>
                        </div>
                    </div>
                    
                    <!-- Panel de Modelos -->
                    <div class="models-panel glass-effect animate-up" style="animation-delay: 0.6s">
                        <div class="panel-header">
                            <div class="panel-title">🎯 MODELOS DE INGRESOS</div>
                            <div class="models-summary">
                                <span class="summary-item">Activos: <b id="stat-activos">0</b></span>
                                <span class="summary-item">Exitosos: <b id="stat-exitosos">0</b></span>
                            </div>
                        </div>
                        <div class="models-list-container">
                            <div class="models-list" id="models-list"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Modal de Configuración -->
                <div class="config-modal" id="config-modal">
                    <div class="modal-content glass-effect">
                        <div class="modal-header">
                            <h2>Centro de Configuración</h2>
                            <button class="btn-close" onclick="dashboard.cerrarConfiguracion()">✕</button>
                        </div>
                        <div class="modal-body">
                            <div class="tabs">
                                <button class="tab-btn active" onclick="dashboard.switchTab('binance')">Binance</button>
                                <button class="tab-btn" onclick="dashboard.switchTab('dolarapp')">DolarApp</button>
                            </div>
                            
                            <div id="tab-binance" class="tab-content active">
                                <div class="config-section">
                                    <h3>🔑 API Binance</h3>
                                    <div class="form-group">
                                        <label>API Key</label>
                                        <input type="password" id="binance-api-key" placeholder="••••••••" />
                                    </div>
                                    <div class="form-group">
                                        <label>API Secret</label>
                                        <input type="password" id="binance-api-secret" placeholder="••••••••" />
                                    </div>
                                    <div class="form-group">
                                        <label>Dirección USDT (TRC-20)</label>
                                        <input type="text" id="binance-address" placeholder="T..." />
                                    </div>
                                    <div class="form-group row">
                                        <input type="checkbox" id="binance-testnet" />
                                        <label for="binance-testnet">Modo Testnet</label>
                                    </div>
                                    <button class="btn btn-primary" id="btn-guardar-binance">GUARDAR CAMBIOS</button>
                                </div>
                            </div>

                            <div id="tab-dolarapp" class="tab-content">
                                <div class="config-section">
                                    <h3>💳 DolarApp Support</h3>
                                    <div class="form-group">
                                        <label>API Key</label>
                                        <input type="password" id="comodolar-api-key" placeholder="••••••••" />
                                    </div>
                                    <div class="form-group">
                                        <label>API Secret</label>
                                        <input type="password" id="comodolar-api-secret" placeholder="••••••••" />
                                    </div>
                                    <button class="btn btn-primary" id="btn-guardar-comodolar">GUARDAR CAMBIOS</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    conectarWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('✅ WebSocket conectado');
            this.agregarLog('✅ Conexión establecida con el núcleo', 'success');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const mensaje = JSON.parse(event.data);
                
                if (mensaje.tipo === 'log') {
                    this.procesarLog(mensaje.data);
                } else if (mensaje.tipo === 'estado') {
                    this.actualizarEstado(mensaje.data);
                }
            } catch (e) {
                console.error('Error procesando mensaje:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ Error WebSocket:', error);
            this.agregarLog('❌ Error de enlace WebSocket', 'error');
        };
        
        this.ws.onclose = () => {
            this.agregarLog('⚠️ Enlace con el servidor perdido', 'error');
            setTimeout(() => {
                if (this.token) this.conectarWebSocket();
            }, 3000);
        };
    }
    
    procesarLog(logData) {
        const mensaje = logData.mensaje || logData.estado_agente || 'Pulso de sistema detectado';
        const tipo = logData.estado_agente === 'ERROR' ? 'error' : 'info';
        this.agregarLog(mensaje, tipo);
    }
    
    agregarLog(mensaje, tipo = 'info') {
        const timestamp = new Date().toLocaleTimeString('es-ES', {
            hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
        
        this.logs.unshift({ mensaje, tipo, timestamp });
        if (this.logs.length > this.maxLogs) this.logs.pop();
        this.renderizarLogs();
    }
    
    renderizarLogs() {
        const container = document.getElementById('logs-container');
        if (!container) return;
        
        container.innerHTML = this.logs.map(log => `
            <div class="log-entry ${log.tipo}">
                <span class="log-timestamp">[${log.timestamp}]</span>
                <span class="log-msg">${log.mensaje}</span>
            </div>
        `).join('');
        container.scrollTop = 0;
    }

    limpiarLogs() {
        this.logs = [];
        this.renderizarLogs();
    }
    
    actualizarEstado(estadoData) {
        this.estado = { ...this.estado, ...estadoData };
        
        const updateEl = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        const ingresos = this.estado.ingresos_totales || 0;
        updateEl('kpi-ingresos', `$${ingresos.toFixed(2)}`);
        updateEl('kpi-activos', this.estado.modelos_activos || 0);
        updateEl('kpi-exitosos', this.estado.modelos_exitosos || 0);
        updateEl('kpi-tasa', `${(this.estado.tasa_exito || 0).toFixed(1)}%`);
        updateEl('ciclos', this.estado.ciclos_completados || 0);
        
        const progressEl = document.getElementById('progress-ingresos');
        if (progressEl) {
            const progreso = Math.min((ingresos / 1000) * 100, 100);
            progressEl.style.width = `${progreso}%`;
        }
        
        updateEl('stat-activos', this.estado.modelos_activos || 0);
        updateEl('stat-exitosos', this.estado.modelos_exitosos || 0);
        updateEl('status-text', this.estado.estado_actual || 'ONLINE');
    }
    
    async cargarEstadoInicial() {
        try {
            const response = await this.apiFetch('/api/configurar/status');
            const data = await response.json();
            
            if (data.binance_configurado) this.agregarLog('💎 Adaptador Binance activo', 'success');
            if (data.comodolar_configurado) this.agregarLog('🌐 Soporte DolarApp cargado', 'success');
            
            const resStatus = await this.apiFetch('/api/status');
            const dataStatus = await resStatus.json();
            this.actualizarEstado(dataStatus);
            this.agregarLog('📊 Matriz de estado sincronizada', 'success');
        } catch (e) {
            console.error('Error cargando estado:', e);
        }
    }
    
    async cargarModelos() {
        try {
            const response = await this.apiFetch('/api/modelos');
            const data = await response.json();
            this.modelos = data.modelos || [];
            this.renderizarModelos();
        } catch (e) {
            console.error('Error cargando modelos:', e);
        }
    }
    
    renderizarModelos() {
        const container = document.getElementById('models-list');
        if (!container) return;
        
        if (this.modelos.length === 0) {
            container.innerHTML = '<div class="empty-state">No se han desplegado modelos aún</div>';
            return;
        }
        
        container.innerHTML = this.modelos.map((modelo, i) => `
            <div class="model-card-item model-${modelo.estado} animate-up" style="animation-delay: ${0.1 * i}s">
                <div class="model-card-header">
                    <span class="model-name">${modelo.estrategia_nombre}</span>
                    <span class="model-badge">${modelo.estado.toUpperCase()}</span>
                </div>
                <div class="model-card-body">
                    <p>${modelo.descripcion || 'Optimizando ejecución...'}</p>
                    <div class="model-footer">
                        <span class="yield">Yield: <b>$${modelo.ingresos_generados.toFixed(2)}</b></span>
                        <span class="date">${new Date(modelo.fecha_creacion).toLocaleDateString()}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    configurarEventos() {
        const listen = (id, evt, fn) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(evt, fn);
        };

        listen('btn-iniciar', 'click', () => this.controlAgente('iniciar'));
        listen('btn-pausar', 'click', () => this.controlAgente('pausar'));
        listen('btn-config', 'click', () => this.mostrarConfiguracion());
        listen('btn-guardar-binance', 'click', () => this.guardarConfigBinance());
        listen('btn-guardar-comodolar', 'click', () => this.guardarConfigComodolar());
        
        setInterval(() => { if (this.token) this.cargarModelos(); }, 15000);
    }
    
    switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        event.target.classList.add('active');
        document.getElementById(`tab-${tab}`).classList.add('active');
    }

    mostrarConfiguracion() {
        document.getElementById('config-modal').style.display = 'flex';
    }
    
    cerrarConfiguracion() {
        document.getElementById('config-modal').style.display = 'none';
    }
    
    async controlAgente(accion) {
        try {
            const response = await this.apiFetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ accion })
            });
            const data = await response.json();
            this.agregarLog(`📡 Comando ${accion}: ${data.mensaje}`, 'success');
        } catch (e) {
            this.agregarLog(`❌ Fallo en comando ${accion}`, 'error');
        }
    }

    async guardarConfigBinance() {
        const payload = {
            api_key: document.getElementById('binance-api-key').value,
            api_secret: document.getElementById('binance-api-secret').value,
            address: document.getElementById('binance-address').value,
            testnet: document.getElementById('binance-testnet').checked
        };
        
        const response = await this.apiFetch('/api/configurar/binance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (response && response.ok) this.agregarLog('✅ Configuración Binance actualizada', 'success');
    }

    async guardarConfigComodolar() {
        const payload = {
            api_key: document.getElementById('comodolar-api-key').value,
            api_secret: document.getElementById('comodolar-api-secret').value
        };
        
        const response = await this.apiFetch('/api/configurar/comodolar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (response && response.ok) this.agregarLog('✅ Configuración DolarApp actualizada', 'success');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    dashboard = new AutomataAIDashboard();
});
