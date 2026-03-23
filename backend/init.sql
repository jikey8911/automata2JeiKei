-- Tabla para almacenar los modelos de ingresos (experimentos)
CREATE TABLE IF NOT EXISTS modelos_ingresos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estrategia_nombre VARCHAR(255) NOT NULL,
    estado VARCHAR(50) NOT NULL CHECK (estado IN ('activo', 'exitoso', 'fallido', 'duplicado')),
    ingresos_generados DECIMAL(15, 2) DEFAULT 0.00,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    datos_metricas JSONB DEFAULT '{}',
    descripcion TEXT,
    plan_ejecucion JSONB DEFAULT '{}',
    modelo_padre_id UUID REFERENCES modelos_ingresos(id) ON DELETE SET NULL
);

-- Tabla para almacenar la base de conocimiento de la IA
CREATE TABLE IF NOT EXISTS base_conocimiento (
    id SERIAL PRIMARY KEY,
    tipo_conocimiento VARCHAR(100) NOT NULL CHECK (tipo_conocimiento IN ('nicho_rentable', 'error_comun', 'herramienta_util', 'estrategia_exitosa', 'tendencia')),
    contenido JSONB NOT NULL,
    relevancia DECIMAL(3, 2) DEFAULT 0.50,
    fecha_aprendizaje TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contador_uso INT DEFAULT 0
);

-- Tabla para almacenar los logs de decisiones de la IA
CREATE TABLE IF NOT EXISTS logs_decision (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado_agente VARCHAR(50) NOT NULL CHECK (estado_agente IN ('INVESTIGANDO', 'FORMULANDO_HIPOTESIS', 'EJECUTANDO', 'ANALIZANDO', 'ADAPTANDO')),
    prompt_enviado TEXT,
    respuesta_recibida TEXT,
    decision_tomada TEXT,
    modelo_id_relacionado UUID REFERENCES modelos_ingresos(id) ON DELETE SET NULL,
    nivel_confianza DECIMAL(3, 2) DEFAULT 0.50
);

-- Tabla para almacenar el estado general del agente
CREATE TABLE IF NOT EXISTS estado_agente (
    id SERIAL PRIMARY KEY,
    estado_actual VARCHAR(50) NOT NULL,
    ingresos_totales DECIMAL(15, 2) DEFAULT 0.00,
    ingresos_semana_actual DECIMAL(15, 2) DEFAULT 0.00,
    modelos_activos INT DEFAULT 0,
    modelos_exitosos INT DEFAULT 0,
    modelos_fallidos INT DEFAULT 0,
    tasa_exito DECIMAL(3, 2) DEFAULT 0.00,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    proxima_ejecucion TIMESTAMP,
    ciclos_completados INT DEFAULT 0
);

-- Índices para optimizar consultas
CREATE INDEX idx_modelos_estado ON modelos_ingresos(estado);
CREATE INDEX idx_modelos_fecha ON modelos_ingresos(fecha_creacion DESC);
CREATE INDEX idx_conocimiento_tipo ON base_conocimiento(tipo_conocimiento);
CREATE INDEX idx_logs_timestamp ON logs_decision(timestamp DESC);
CREATE INDEX idx_logs_estado ON logs_decision(estado_agente);

-- Insertar estado inicial del agente
INSERT INTO estado_agente (estado_actual, proxima_ejecucion) 
VALUES ('INICIALIZADO', CURRENT_TIMESTAMP + INTERVAL '1 minute')
ON CONFLICT DO NOTHING;
