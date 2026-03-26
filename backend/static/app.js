// ============================================
// AutomataAI Dashboard - JavaScript
// ============================================

let dashboard;

class AutomataAIDashboard {
    constructor() {
        this.ws = null;
        this.logs = [];
        this.maxLogs = 100;
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
    
    init() {
        this.renderDashboard();
        this.conectarWebSocket();
        this.cargarEstadoInicial();
        this.cargarModelos();
        this.configurarEventos();
    }
    
    renderDashboard() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="dashboard">
                <header class="header">
                    <h1>⚙️ AUTOMATA AI</h1>
                    <div class="header-status">
                        <div class="status-badge">
                            <div class="status-dot"></div>
                            <span id="status-text">INICIALIZANDO</span>
                        </div>
                    </div>
                </header>
                
                <div class="main-content">
                    <!-- Panel de KPIs -->
                    <div class="kpi-panel">
                        <div class="kpi-card">
                            <div class="kpi-label">Ingresos Totales (USDT)</div>
                            <div class="kpi-value" id="kpi-ingresos">$0.00</div>
                            <div class="kpi-change">Meta semanal: $1,000</div>
                            <div class="progress-bar">
                                <div class="progress-fill" id="progress-ingresos" style="width: 0%"></div>
                            </div>
                        </div>
                        
                        <div class="kpi-card">
                            <div class="kpi-label">Modelos Activos</div>
                            <div class="kpi-value" id="kpi-activos">0</div>
                            <div class="kpi-change">En ejecución</div>
                        </div>
                        
                        <div class="kpi-card">
                            <div class="kpi-label">Modelos Exitosos</div>
                            <div class="kpi-value" id="kpi-exitosos">0</div>
                            <div class="kpi-change">Duplicados</div>
                        </div>
                        
                        <div class="kpi-card">
                            <div class="kpi-label">Tasa de Éxito</div>
                            <div class="kpi-value" id="kpi-tasa">0%</div>
                            <div class="kpi-change">Ciclos: <span id="ciclos">0</span></div>
                        </div>
                    </div>
                    
                    <!-- Panel de Logs -->
                    <div class="logs-panel">
                        <div class="logs-header">📡 Pensamiento en Vivo</div>
                        <div class="logs-container" id="logs-container"></div>
                        <div class="button-group">
                            <button class="btn" id="btn-iniciar">Iniciar Agente</button>
                            <button class="btn" id="btn-pausar">Pausar</button>
                            <button class="btn btn-config" id="btn-config">⚙️ Configurar</button>
                        </div>
                    </div>
                    
                    <!-- Panel de Modelos -->
                    <div class="models-panel">
                        <div class="models-header">🎯 Modelos de Ingresos</div>
                        <div class="models-stats">
                            <div class="stat-item">
                                <div class="stat-number" id="stat-activos">0</div>
                                <div class="stat-label">Activos</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number" id="stat-exitosos">0</div>
                                <div class="stat-label">Exitosos</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number" id="stat-fallidos">0</div>
                                <div class="stat-label">Fallidos</div>
                            </div>
                        </div>
                        <div class="models-list" id="models-list"></div>
                    </div>
                </div>
                
                <!-- Modal de Configuración -->
                <div class="config-modal" id="config-modal">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h2>Configuración del Sistema</h2>
                            <button class="btn-close" onclick="dashboard.cerrarConfiguracion()">✕</button>
                        </div>
                        <div class="modal-body">
                            <div class="config-section">
                                <h3>🔑 Credenciales de Binance</h3>
                                <p class="config-desc">Ingresa tus credenciales de Binance para habilitar transferencias automáticas de ingresos</p>
                                <div class="form-group">
                                    <label>API Key</label>
                                    <input type="password" id="binance-api-key" placeholder="Tu API Key de Binance" />
                                </div>
                                <div class="form-group">
                                    <label>API Secret</label>
                                    <input type="password" id="binance-api-secret" placeholder="Tu API Secret de Binance" />
                                </div>
                                <div class="form-group">
                                    <label>Dirección de Destino (USDT)</label>
                                    <input type="text" id="binance-address" placeholder="Dirección TRON o Ethereum para recibir USDT" />
                                </div>
                                <div class="form-group checkbox">
                                    <input type="checkbox" id="binance-testnet" />
                                    <label for="binance-testnet">Usar Testnet (desarrollo)</label>
                                </div>
                                <button class="btn btn-primary" id="btn-guardar-binance">💾 Guardar Configuración</button>
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
            this.agregarLog('✅ Conexión establecida con el servidor', 'success');
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
            this.agregarLog('❌ Error de conexión', 'error');
        };
        
        this.ws.onclose = () => {
            console.log('⚠️ WebSocket desconectado');
            this.agregarLog('⚠️ Desconectado del servidor', 'error');
            // Reconectar después de 3 segundos
            setTimeout(() => this.conectarWebSocket(), 3000);
        };
    }
    
    procesarLog(logData) {
        const mensaje = logData.mensaje || logData.estado_agente || 'Sin mensaje';
        const tipo = logData.estado_agente === 'ERROR' ? 'error' : 'info';
        
        this.agregarLog(mensaje, tipo);
    }
    
    agregarLog(mensaje, tipo = 'info') {
        const timestamp = new Date().toLocaleTimeString('es-ES', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        this.logs.unshift({ mensaje, tipo, timestamp });
        
        if (this.logs.length > this.maxLogs) {
            this.logs.pop();
        }
        
        this.renderizarLogs();
    }
    
    renderizarLogs() {
        const container = document.getElementById('logs-container');
        
        container.innerHTML = this.logs.map(log => `
            <div class="log-entry ${log.tipo}">
                <span class="log-timestamp">[${log.timestamp}]</span>
                <span>${log.mensaje}</span>
            </div>
        `).join('');
        
        // Auto-scroll al final
        container.scrollTop = container.scrollHeight;
    }
    
    actualizarEstado(estadoData) {
        this.estado = { ...this.estado, ...estadoData };
        
        // Actualizar KPIs
        const ingresos = this.estado.ingresos_totales || 0;
        document.getElementById('kpi-ingresos').textContent = `$${ingresos.toFixed(2)}`;
        document.getElementById('kpi-activos').textContent = this.estado.modelos_activos || 0;
        document.getElementById('kpi-exitosos').textContent = this.estado.modelos_exitosos || 0;
        document.getElementById('kpi-tasa').textContent = `${(this.estado.tasa_exito || 0).toFixed(1)}%`;
        document.getElementById('ciclos').textContent = this.estado.ciclos_completados || 0;
        
        // Actualizar barra de progreso
        const progreso = Math.min((ingresos / 1000) * 100, 100);
        document.getElementById('progress-ingresos').style.width = `${progreso}%`;
        
        // Actualizar estadísticas de modelos
        document.getElementById('stat-activos').textContent = this.estado.modelos_activos || 0;
        document.getElementById('stat-exitosos').textContent = this.estado.modelos_exitosos || 0;
        document.getElementById('stat-fallidos').textContent = this.estado.modelos_fallidos || 0;
        
        // Actualizar estado del agente
        document.getElementById('status-text').textContent = this.estado.estado_actual || 'DESCONOCIDO';
    }
    
    async cargarEstadoInicial() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            this.actualizarEstado(data);
            this.agregarLog('📊 Estado inicial cargado', 'success');
        } catch (e) {
            console.error('Error cargando estado:', e);
            this.agregarLog('❌ Error cargando estado inicial', 'error');
        }
    }
    
    async cargarModelos() {
        try {
            const response = await fetch('/api/modelos');
            const data = await response.json();
            this.modelos = data.modelos || [];
            this.renderizarModelos();
        } catch (e) {
            console.error('Error cargando modelos:', e);
        }
    }
    
    renderizarModelos() {
        const container = document.getElementById('models-list');
        
        if (this.modelos.length === 0) {
            container.innerHTML = '<div class="empty-state">Sin modelos aún</div>';
            return;
        }
        
        container.innerHTML = this.modelos.map(modelo => `
            <div class="model-card model-${modelo.estado}">
                <div class="model-header">
                    <h4>${modelo.estrategia_nombre}</h4>
                    <span class="model-badge model-${modelo.estado}">${modelo.estado.toUpperCase()}</span>
                </div>
                <div class="model-body">
                    <p class="model-desc">${modelo.descripcion || 'Sin descripción'}</p>
                    <div class="model-stats">
                        <div class="model-stat">
                            <span class="stat-label">Ingresos:</span>
                            <span class="stat-value">$${modelo.ingresos_generados.toFixed(2)}</span>
                        </div>
                        <div class="model-stat">
                            <span class="stat-label">Creado:</span>
                            <span class="stat-value">${new Date(modelo.fecha_creacion).toLocaleDateString('es-ES')}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    configurarEventos() {
        document.getElementById('btn-iniciar').addEventListener('click', () => {
            this.iniciarAgente();
        });
        
        document.getElementById('btn-pausar').addEventListener('click', () => {
            this.pausarAgente();
        });
        
        document.getElementById('btn-config').addEventListener('click', () => {
            this.mostrarConfiguracion();
        });
        
        document.getElementById('btn-guardar-binance').addEventListener('click', () => {
            this.guardarConfigBinance();
        });
        
        // Cargar modelos cada 15 segundos
        setInterval(() => this.cargarModelos(), 15000);
    }
    
    mostrarConfiguracion() {
        const modal = document.getElementById('config-modal');
        modal.style.display = 'flex';
    }
    
    cerrarConfiguracion() {
        const modal = document.getElementById('config-modal');
        modal.style.display = 'none';
    }
    
    async guardarConfigBinance() {
        const apiKey = document.getElementById('binance-api-key').value;
        const apiSecret = document.getElementById('binance-api-secret').value;
        const address = document.getElementById('binance-address').value;
        const testnet = document.getElementById('binance-testnet').checked;
        
        if (!apiKey || !apiSecret || !address) {
            this.agregarLog('❌ Todos los campos son requeridos', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/configurar/binance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_key: apiKey,
                    api_secret: apiSecret,
                    address: address,
                    testnet: testnet
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.agregarLog('✅ Configuración de Binance guardada', 'success');
                this.cerrarConfiguracion();
                // Limpiar campos
                document.getElementById('binance-api-key').value = '';
                document.getElementById('binance-api-secret').value = '';
                document.getElementById('binance-address').value = '';
            } else {
                this.agregarLog(`❌ Error: ${data.detail || 'Error desconocido'}`, 'error');
            }
        } catch (e) {
            console.error('Error guardando configuración:', e);
            this.agregarLog('❌ Error al guardar configuración', 'error');
        }
    }
    
    async iniciarAgente() {
        try {
            const response = await fetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ accion: 'iniciar' })
            });
            
            const data = await response.json();
            this.agregarLog(`✅ ${data.mensaje}`, 'success');
        } catch (e) {
            console.error('Error iniciando agente:', e);
            this.agregarLog('❌ Error al iniciar agente', 'error');
        }
    }
    
    async pausarAgente() {
        try {
            const response = await fetch('/api/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ accion: 'pausar' })
            });
            
            const data = await response.json();
            this.agregarLog(`⏸️ ${data.mensaje}`, 'success');
        } catch (e) {
            console.error('Error pausando agente:', e);
            this.agregarLog('❌ Error al pausar agente', 'error');
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new AutomataAIDashboard();
});
