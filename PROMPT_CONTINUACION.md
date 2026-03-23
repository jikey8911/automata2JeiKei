# 🚀 Prompt de Continuación - Fase 2: Sistema Completo

Este documento contiene el prompt detallado para continuar el desarrollo del sistema AutomataAI desde el MVP hasta una solución de producción completa.

---

## 📋 Contexto del Proyecto

El sistema actual (MVP) consiste en un agente de IA autónomo basado en Arquitectura Hexagonal. Utiliza Docker Compose con tres servicios: `agente` (Python), `db` (PostgreSQL) y `ollama` (LLM local). El agente ya puede investigar en la web (usando DuckDuckGo), razonar (usando Ollama), y persistir sus "Modelos de Ingresos" y "Conocimiento" en PostgreSQL. La ejecución de acciones es actualmente simulada (imprime en consola).

**Repositorio**: https://github.com/jikey8911/AutomataAiJeiKei

---

## 🎯 Objetivo de la Fase 2

Evolucionar el MVP a un sistema de producción completo, implementando:

1. **Ejecución Real de Acciones** mediante automatización de Android virtual
2. **Integración de Pagos** con Binance para transferencia de ingresos
3. **Dashboard Avanzado** con SvelteKit, Tailwind y componentes del jeikei-design-system
4. **Sistema de Persistencia Mejorado** con sincronización en tiempo real
5. **Monitoreo y Alertas** para supervisión del agente

---

## 🏗️ Tareas de Desarrollo (Fase 2)

### **Tarea 2.1: Implementar el Adaptador de Android Virtual (Appium)**

**Objetivo**: Permitir que la IA automatice acciones en aplicaciones móviles.

**Acciones**:

1. **Crear un nuevo contenedor Docker en `docker-compose.yml`**:
   - Nombre: `android_emulator`
   - Imagen: `budtmo/docker-android-x86-11.0` o similar
   - Exponer puerto 4723 para Appium
   - Configurar volúmenes para persistencia

2. **Crear `backend/adaptadores/appium_adapter.py`**:
   - Implementar interfaz `IAutomatizadorUI` (crear este puerto en `backend/puertos/automatizador.py`)
   - Métodos principales:
     - `async def tocar_elemento(elemento_id: str) -> bool`
     - `async def escribir_texto(elemento_id: str, texto: str) -> bool`
     - `async def instalar_app(url_apk: str) -> bool`
     - `async def obtener_captura_pantalla() -> bytes`
     - `async def ejecutar_script_personalizado(script: str) -> dict`
   - Usar librería `appium-python-client`
   - Manejar reconexiones automáticas

3. **Integrar en el agente**:
   - Registrar el adaptador en `backend/dominio/agente.py`
   - Crear método `_ejecutar_en_android()` que use el adaptador
   - Implementar scripts de automatización para:
     - Crear cuentas en redes sociales (TikTok, Instagram)
     - Publicar contenido
     - Interactuar con apps de recompensas

**Criterios de Aceptación**:
- El adaptador se conecta exitosamente a Appium
- Puede tocar elementos, escribir texto e instalar apps
- Los errores se manejan gracefully con reintentos

---

### **Tarea 2.2: Implementar el Adaptador de Pagos (Binance API)**

**Objetivo**: Permitir que la IA transfiera ingresos a la cuenta del usuario.

**Acciones**:

1. **Crear `backend/adaptadores/binance_adapter.py`**:
   - Implementar interfaz `IServicioFinanciero` (crear este puerto en `backend/puertos/financiero.py`)
   - Métodos principales:
     - `async def consultar_balance(simbolo: str = "USDT") -> float`
     - `async def enviar_usdt(direccion: str, monto: float) -> dict`
     - `async def obtener_historial_transacciones() -> List[dict]`
     - `async def obtener_tasa_cambio() -> dict`
   - Usar librería `python-binance`
   - Implementar validaciones de seguridad:
     - Verificar saldo suficiente
     - Validar dirección de destino
     - Registrar todas las transacciones

2. **Gestión de Credenciales**:
   - Las claves de API deben cargarse desde variables de entorno
   - Implementar rotación de claves
   - Usar `webdev_request_secrets` para configurar las claves

3. **Lógica de Transferencia**:
   - Crear método en `AgenteAutonomo` para transferir ingresos
   - Condiciones para transferencia:
     - Ingresos acumulados >= $100 (configurable)
     - Transferencia semanal automática
     - Log de cada transacción en BD

**Criterios de Aceptación**:
- El adaptador se conecta a Binance exitosamente
- Puede consultar balance y realizar transferencias
- Todas las transacciones se registran en la BD
- Manejo robusto de errores de red

---

### **Tarea 2.3: Crear la API del Dashboard Avanzada**

**Objetivo**: Exponer endpoints REST y WebSocket para el dashboard frontend.

**Acciones**:

1. **Extender `backend/main.py`** con nuevos endpoints:
   - `GET /api/modelos/{id}` - Obtener detalles de un modelo
   - `GET /api/conocimiento?tipo=nicho_rentable` - Obtener conocimiento por tipo
   - `GET /api/logs?limit=50&estado=EJECUTANDO` - Obtener logs filtrados
   - `GET /api/transacciones` - Historial de transferencias
   - `POST /api/modelos` - Crear modelo manualmente (admin)
   - `DELETE /api/modelos/{id}` - Eliminar modelo
   - `GET /api/estadisticas/semanal` - Estadísticas semanales

2. **Mejorar WebSocket `/ws/logs`**:
   - Enviar eventos de transacciones
   - Enviar alertas de modelos exitosos
   - Enviar notificaciones de errores críticos
   - Implementar heartbeat para detectar desconexiones

3. **Autenticación y Autorización**:
   - Implementar autenticación básica o JWT
   - Solo el propietario puede controlar el agente
   - Logs públicos (opcional) para demostración

**Criterios de Aceptación**:
- Todos los endpoints responden correctamente
- WebSocket mantiene conexión estable
- Datos se actualizan en tiempo real

---

### **Tarea 2.4: Construir el Frontend con SvelteKit**

**Objetivo**: Crear un dashboard profesional y reactivo.

**Acciones**:

1. **Configurar SvelteKit**:
   - Crear proyecto en `frontend/`
   - Instalar dependencias: Tailwind CSS 4, shadcn/svelte
   - Configurar para servirse desde el backend FastAPI

2. **Componentes Principales**:
   - `Dashboard.svelte` - Página principal
   - `KPICard.svelte` - Tarjeta de KPI con animaciones
   - `LogViewer.svelte` - Visor de logs en tiempo real
   - `ModelsList.svelte` - Tabla de modelos con filtros
   - `TransactionHistory.svelte` - Historial de transacciones
   - `AgentControls.svelte` - Botones de control del agente

3. **Estilos jeikei-design-system**:
   - Usar colores: `--neon-green: #00ff99`, `--bg-primary: #05070a`
   - Componentes glassmorphism con `backdrop-filter: blur(10px)`
   - Tipografía monoespaciada para datos (Fira Code)
   - Animaciones suaves y efectos de glow

4. **Funcionalidades**:
   - Conexión WebSocket en tiempo real
   - Gráficos de ingresos (Chart.js o Recharts)
   - Filtros y búsqueda de modelos
   - Exportar datos a CSV
   - Modo oscuro/claro (preferencia)

**Criterios de Aceptación**:
- Dashboard carga en < 2 segundos
- WebSocket conecta automáticamente
- Todos los datos se actualizan en tiempo real
- Responsive en móvil y desktop

---

### **Tarea 2.5: Implementar Sistema de Ciclo de Vida Completo**

**Objetivo**: Completar el ciclo de vida de los modelos con ejecución real.

**Acciones**:

1. **Mejorar Fase de Ejecución**:
   - En lugar de simular, ejecutar acciones reales en Android
   - Crear scripts específicos para cada estrategia:
     - Script de TikTok: crear cuenta, publicar video
     - Script de Fiverr: crear gig, esperar órdenes
     - Script de Medium: publicar artículo
   - Registrar cada acción en logs

2. **Mejorar Fase de Análisis**:
   - Consultar APIs reales para obtener métricas:
     - Número de vistas en TikTok
     - Número de clics en afiliados
     - Número de órdenes en Fiverr
   - Usar web scraping si es necesario
   - Actualizar ingresos en tiempo real

3. **Sistema de Alertas**:
   - Alertar si un modelo genera ingresos
   - Alertar si un modelo falla 3 veces
   - Alertar si se alcanza la meta semanal
   - Notificaciones por email (opcional)

**Criterios de Aceptación**:
- Modelos se ejecutan en Android real
- Ingresos se registran correctamente
- Alertas se envían en tiempo real

---

### **Tarea 2.6: Optimización y Producción**

**Objetivo**: Preparar el sistema para producción.

**Acciones**:

1. **Performance**:
   - Optimizar queries de BD con índices
   - Implementar caché en Redis
   - Comprimir logs antiguos
   - Limitar tamaño de logs en memoria

2. **Seguridad**:
   - Validar todas las entradas
   - Usar HTTPS en producción
   - Encriptar credenciales en BD
   - Implementar rate limiting

3. **Monitoreo**:
   - Agregar métricas Prometheus
   - Crear dashboards en Grafana
   - Alertas en Slack/Discord
   - Logs centralizados (ELK stack opcional)

4. **Testing**:
   - Tests unitarios para adaptadores
   - Tests de integración para el agente
   - Tests E2E para el dashboard
   - Coverage > 80%

**Criterios de Aceptación**:
- Sistema soporta 24/7 sin caídas
- Respuestas < 200ms
- Seguridad validada

---

## 🔄 Flujo de Trabajo Recomendado

1. **Completar Tarea 2.1** (Appium) - 2-3 días
2. **Completar Tarea 2.2** (Binance) - 1-2 días
3. **Completar Tarea 2.3** (API avanzada) - 1 día
4. **Completar Tarea 2.4** (Frontend) - 3-4 días
5. **Completar Tarea 2.5** (Ciclo de vida) - 2-3 días
6. **Completar Tarea 2.6** (Producción) - 2-3 días

**Tiempo total estimado**: 2-3 semanas

---

## 📚 Recursos Útiles

- [Appium Python Client](https://github.com/appium/python-client)
- [python-binance](https://github.com/sammchardy/python-binance)
- [SvelteKit Docs](https://kit.svelte.dev/)
- [Tailwind CSS 4](https://tailwindcss.com/)
- [jeikei-design-system](https://github.com/jikey8911/jeikei-design-system)

---

## ✅ Checklist de Validación

- [ ] Appium se conecta al emulador
- [ ] Binance API funciona con credenciales
- [ ] Todos los endpoints REST responden
- [ ] WebSocket mantiene conexión 24/7
- [ ] Frontend carga sin errores
- [ ] Ciclo completo ejecuta sin fallos
- [ ] Dashboard muestra datos en tiempo real
- [ ] Sistema soporta 24/7 sin interrupciones

---

## 🎓 Notas Importantes

1. **Seguridad**: Nunca hardcodear credenciales. Usar variables de entorno.
2. **Testing**: Probar cada adaptador independientemente antes de integrar.
3. **Documentación**: Mantener README.md actualizado con cambios.
4. **Versionado**: Usar semantic versioning (v1.0.0, v1.1.0, etc.)
5. **Backup**: Hacer backup de la BD antes de cambios importantes.

---

**¡Listo para continuar el desarrollo!** 🚀
