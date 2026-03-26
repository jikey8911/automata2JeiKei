# 🚀 AutomataAI - Prompt de Continuación Fase 3

## 📋 Índice
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Funcionamiento Actual (Fase 2.5)](#funcionamiento-actual-fase-25)
4. [Fase 3 - Implementación Real](#fase-3---implementación-real)
5. [Guía de Desarrollo](#guía-de-desarrollo)
6. [Comandos Útiles](#comandos-útiles)

---

## 📖 Descripción General

**AutomataAI** es un sistema de inteligencia artificial autónomo que genera ingresos desde cero mediante:

- **Investigación Autónoma**: Busca en internet nuevas formas de monetización
- **Formulación de Hipótesis**: Usa LLMs locales (Ollama) para crear estrategias
- **Ejecución**: Ejecuta modelos de ingresos (simulado en MVP, real en Fase 3)
- **Análisis**: Evalúa resultados y aprende de fracasos
- **Adaptación**: Duplica modelos exitosos, elimina fallidos

**Objetivo Final**: Generar **$1,000 USDT** en la primera semana, transferidos automáticamente a Binance.

---

## 🏗️ Arquitectura del Sistema

### Arquitectura Hexagonal (Puertos y Adaptadores)

```
┌─────────────────────────────────────────────────────────────┐
│                    NÚCLEO (DOMINIO)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  AgenteAutonomo                                        │ │
│  │  - Ciclo de investigación-hipótesis-ejecución         │ │
│  │  - Gestión de modelos de ingresos                     │ │
│  │  - Toma de decisiones autónoma                        │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  BaseDeConocimiento                                    │ │
│  │  - Almacena estrategias aprendidas                    │ │
│  │  - Historial de decisiones                            │ │
│  │  - Patrones de éxito/fracaso                          │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ModeloIngresos                                        │ │
│  │  - Ciclo de vida: Creación → Ejecución → Análisis    │ │
│  │  - Estados: ACTIVO, EXITOSO, FALLIDO, DUPLICADO      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ↑                    ↑                    ↑
     PUERTOS             PUERTOS              PUERTOS
        ↓                    ↓                    ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Repositorio  │  │ Buscador Web │  │ Generador    │
│ (PostgreSQL) │  │ (DuckDuckGo) │  │ Lenguaje     │
│              │  │              │  │ (Ollama)     │
└──────────────┘  └──────────────┘  └──────────────┘
        ↓                    ↓                    ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ PostgreSQL   │  │ API Web      │  │ Ollama Local │
│ Adapter      │  │ Adapter      │  │ Adapter      │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Estructura de Directorios

```
AutomataAiJeiKei/
├── backend/
│   ├── puertos/                    # Interfaces (contratos)
│   │   ├── repositorio.py          # IRepositorio
│   │   ├── buscador.py             # IBuscadorWeb
│   │   ├── lenguaje.py             # IGeneradorDeLenguaje
│   │   ├── automatizador.py        # IAutomatizadorUI (Appium)
│   │   └── financiero.py           # IServicioFinanciero (Binance)
│   ├── dominio/                    # Lógica de negocio
│   │   ├── agente.py               # AgenteAutonomo
│   │   ├── base_conocimiento.py    # BaseDeConocimiento
│   │   └── estrategias.py          # Estrategias de ejecución
│   ├── adaptadores/                # Implementaciones
│   │   ├── postgres_adapter.py     # PostgreSQL
│   │   ├── duckduckgo_adapter.py   # DuckDuckGo
│   │   ├── ollama_adapter.py       # Ollama
│   │   ├── appium_adapter.py       # Appium (Android)
│   │   └── binance_adapter.py      # Binance API
│   ├── main.py                     # FastAPI + WebSocket
│   ├── rutas_avanzadas.py          # Endpoints REST
│   ├── rutas_configuracion.py      # Config endpoints
│   ├── static/                     # Frontend
│   │   ├── index.html              # Dashboard
│   │   ├── app.js                  # Lógica del dashboard
│   │   └── styles.css              # Estilos jeikei-design-system
│   ├── Dockerfile                  # Contenedor Python
│   ├── requirements.txt            # Dependencias
│   └── init.sql                    # Schema de BD
├── docker-compose.yml              # Orquestación (v1)
├── docker-compose-local.yml        # Orquestación (v2 - localhost)
├── docker-compose.v2.yml           # Orquestación (v2 - Android)
├── README.md                       # Documentación principal
├── QUICKSTART.md                   # Guía rápida
├── FASE2_RESUMEN.md               # Resumen de Fase 2
└── PROMPT_CONTINUACION.md         # Este archivo
```

---

## 🔄 Funcionamiento Actual (Fase 2.5)

### Ciclo de Operación del Agente

El agente ejecuta continuamente este ciclo cada 5 minutos:

```
┌─────────────────────────────────────────────────────────┐
│ FASE 1: INVESTIGACIÓN (2-3 minutos)                    │
├─────────────────────────────────────────────────────────┤
│ 1. Busca en DuckDuckGo: "formas de generar ingresos"   │
│ 2. Extrae URLs relevantes                              │
│ 3. Obtiene contenido de páginas                        │
│ 4. Almacena en BaseDeConocimiento                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ FASE 2: FORMULACIÓN DE HIPÓTESIS (1-2 minutos)         │
├─────────────────────────────────────────────────────────┤
│ 1. Usa Ollama (Mixtral) para analizar datos            │
│ 2. Genera 3-5 hipótesis de negocio                     │
│ 3. Evalúa viabilidad de cada una                       │
│ 4. Selecciona la mejor según criterios                 │
│ 5. Crea ModeloIngresos con descripción                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ FASE 3: EJECUCIÓN (Simulada en MVP)                    │
├─────────────────────────────────────────────────────────┤
│ ACTUAL (Fase 2.5):                                     │
│ - Simula ejecución del modelo                          │
│ - Genera ingresos aleatorios ($0-$100)                 │
│ - Registra en BD                                       │
│                                                        │
│ FASE 3 (Real):                                         │
│ - Ejecuta estrategia real (ej: crear cuenta en app)   │
│ - Usa Appium para automatizar UI                       │
│ - Monitorea resultados en tiempo real                  │
│ - Registra ingresos reales                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ FASE 4: ANÁLISIS (1 minuto)                            │
├─────────────────────────────────────────────────────────┤
│ 1. Evalúa si modelo fue exitoso                        │
│ 2. Calcula ROI y rentabilidad                          │
│ 3. Marca estado: EXITOSO o FALLIDO                     │
│ 4. Almacena métricas en BD                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ FASE 5: ADAPTACIÓN (30 segundos)                       │
├─────────────────────────────────────────────────────────┤
│ 1. Si EXITOSO: Duplica el modelo (crea 2 copias)      │
│ 2. Si FALLIDO: Marca para eliminación                  │
│ 3. Actualiza BaseDeConocimiento                        │
│ 4. Prepara próximo ciclo                               │
└─────────────────────────────────────────────────────────┘
```

### Dashboard en Tiempo Real

**URL**: `http://localhost:8000/`

**Componentes**:

1. **Header**: Estado del agente (ACTIVO/PAUSADO/ERROR)
2. **KPI Panel**: 
   - Ingresos totales (USDT)
   - Modelos activos
   - Modelos exitosos
   - Tasa de éxito (%)
   - Barra de progreso hacia $1,000

3. **Logs en Vivo**: Pensamiento del agente en tiempo real (WebSocket)
4. **Modelos**: Tarjetas con estado visual de cada modelo
5. **Configuración**: Modal para ingresar credenciales de Binance

### API REST Endpoints

```
# Control del Agente
POST   /api/control                    → Iniciar/Pausar agente
GET    /api/status                     → Estado actual
GET    /api/modelos                    → Listar modelos
GET    /api/logs                       → Historial de logs

# Configuración
POST   /api/configurar/binance         → Guardar credenciales Binance
GET    /api/configurar/binance/status  → Estado de configuración
GET    /api/sistema/info               → Info del sistema

# WebSocket
WS     /ws/logs                        → Stream de logs en vivo
```

---

## 🚀 Fase 3 - Implementación Real

### 3.1 Integración Real de Binance

**Archivo**: `backend/adaptadores/binance_adapter.py`

**Cambios Necesarios**:

```python
# ACTUAL (Simulado)
async def obtener_balance(self) -> float:
    return random.uniform(0, 100)  # Simulado

# FASE 3 (Real)
from binance.client import Client
from binance.exceptions import BinanceAPIException

class BinanceAdapterReal(IServicioFinanciero):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.client = Client(api_key, api_secret, testnet=testnet)
    
    async def obtener_balance(self) -> float:
        """Obtener balance real de USDT"""
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == 'USDT':
                    return float(balance['free'])
        except BinanceAPIException as e:
            logger.error(f"Error Binance: {e}")
            return 0.0
    
    async def enviar_transferencia(self, 
                                  cantidad: float, 
                                  direccion: str) -> str:
        """Enviar USDT a dirección"""
        try:
            # Validar cantidad
            if cantidad <= 0:
                raise ValueError("Cantidad debe ser > 0")
            
            # Realizar transferencia
            tx = self.client.withdraw(
                coin='USDT',
                withdrawOrderId=None,
                network='TRX',  # TRON network
                address=direccion,
                amount=cantidad
            )
            return tx['id']
        except Exception as e:
            logger.error(f"Error transferencia: {e}")
            raise
```

**Instalación**:
```bash
pip install python-binance
```

### 3.2 Ejecución Real de Estrategias

**Archivo**: `backend/dominio/estrategias.py`

**Estrategias a Implementar**:

#### Estrategia 1: Arbitraje de Criptomonedas
```python
class EstrategiaArbitraje(EstrategiaBase):
    """
    Compra criptomonedas en exchange A (precio bajo)
    Vende en exchange B (precio alto)
    Ganancia = Diferencia de precio - Comisiones
    """
    
    async def ejecutar(self) -> float:
        # 1. Obtener precios en múltiples exchanges
        # 2. Identificar oportunidades
        # 3. Ejecutar compra/venta
        # 4. Retornar ganancia
        pass
```

#### Estrategia 2: Tareas Micro (Fiverr, Upwork)
```python
class EstrategiaTareasMicro(EstrategiaBase):
    """
    Automatiza creación de gigs en Fiverr
    Completa tareas simples
    Genera ingresos por servicio
    """
    
    async def ejecutar(self) -> float:
        # 1. Usar Appium para automatizar UI
        # 2. Crear gig con descripción generada por IA
        # 3. Esperar clientes
        # 4. Completar tareas automáticamente
        # 5. Retornar ingresos
        pass
```

#### Estrategia 3: Dropshipping Automatizado
```python
class EstrategiaDropshipping(EstrategiaBase):
    """
    Crea tienda online automatizada
    Importa productos de AliExpress
    Vende en Shopify/WooCommerce
    """
    
    async def ejecutar(self) -> float:
        # 1. Crear cuenta en plataforma
        # 2. Importar productos
        # 3. Configurar precios
        # 4. Esperar ventas
        # 5. Retornar ganancia
        pass
```

#### Estrategia 4: Contenido Generado por IA
```python
class EstrategiaContenidoIA(EstrategiaBase):
    """
    Genera contenido (artículos, videos, imágenes)
    Monetiza con AdSense, Patreon, etc.
    """
    
    async def ejecutar(self) -> float:
        # 1. Generar contenido con Ollama
        # 2. Publicar en plataformas
        # 3. Monetizar
        # 4. Recolectar ingresos
        # 5. Retornar ganancia
        pass
```

### 3.3 Transferencias Automáticas

**Lógica de Transferencia**:

```python
async def transferir_ingresos_a_binance(self):
    """
    Ejecuta cada vez que se alcanza un hito de ingresos
    """
    config = cargar_configuracion()
    binance_config = config.get('binance', {})
    
    if not binance_config:
        logger.warning("Binance no configurado")
        return
    
    # Obtener ingresos totales
    ingresos_totales = await self.db.obtener_ingresos_totales()
    ingresos_transferidos = await self.db.obtener_ingresos_transferidos()
    disponible = ingresos_totales - ingresos_transferidos
    
    # Transferir si hay disponible
    if disponible >= 10:  # Mínimo $10
        try:
            tx_id = await self.binance.enviar_transferencia(
                cantidad=disponible,
                direccion=binance_config['address']
            )
            
            # Registrar transferencia
            await self.db.registrar_transferencia(
                cantidad=disponible,
                tx_id=tx_id,
                timestamp=datetime.now()
            )
            
            # Notificar al usuario
            await self.notificar(
                f"✅ Transferencia de ${disponible:.2f} USDT completada",
                f"TX: {tx_id}"
            )
        except Exception as e:
            logger.error(f"Error en transferencia: {e}")
            await self.notificar(
                f"❌ Error en transferencia: {str(e)}",
                "Revisa configuración de Binance"
            )
```

### 3.4 Appium + Android Virtual

**Instalación**:

```bash
# Instalar Appium
npm install -g appium

# Instalar driver de Android
appium driver install uiautomator2

# Iniciar Appium
appium --port 4723
```

**Uso en Código**:

```python
from appium import webdriver

class AppiumAdapterReal(IAutomatizadorUI):
    def __init__(self, appium_url: str = "http://localhost:4723"):
        self.appium_url = appium_url
        self.driver = None
    
    async def conectar(self):
        """Conectar a dispositivo Android"""
        capabilities = {
            "platformName": "Android",
            "deviceName": "emulator-5554",
            "app": "/path/to/app.apk",
            "automationName": "UiAutomator2"
        }
        self.driver = webdriver.Remote(
            self.appium_url,
            capabilities
        )
    
    async def tocar(self, x: int, y: int):
        """Tocar pantalla en coordenadas"""
        self.driver.tap([(x, y)])
    
    async def escribir(self, texto: str):
        """Escribir texto"""
        self.driver.send_keys(texto)
```

### 3.5 Testing Completo

**Pytest para Backend**:

```python
# tests/test_binance_adapter.py
import pytest
from adaptadores.binance_adapter import BinanceAdapterReal

@pytest.mark.asyncio
async def test_obtener_balance():
    adapter = BinanceAdapterReal(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    balance = await adapter.obtener_balance()
    assert isinstance(balance, float)
    assert balance >= 0

@pytest.mark.asyncio
async def test_enviar_transferencia():
    adapter = BinanceAdapterReal(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    tx_id = await adapter.enviar_transferencia(
        cantidad=10,
        direccion="TN3W4H6rK833ixS4mMeVGcP1Mfb5eyJD92"
    )
    assert isinstance(tx_id, str)
```

### 3.6 Monitoreo y Alertas

**Prometheus Metrics**:

```python
from prometheus_client import Counter, Gauge, Histogram

# Métricas
modelos_creados = Counter('modelos_creados_total', 'Total de modelos creados')
modelos_exitosos = Counter('modelos_exitosos_total', 'Total de modelos exitosos')
ingresos_generados = Gauge('ingresos_generados_usdt', 'Ingresos en USDT')
tiempo_ciclo = Histogram('tiempo_ciclo_segundos', 'Tiempo de ciclo en segundos')

# En el agente
@tiempo_ciclo.time()
async def ejecutar_ciclo(self):
    # ... código ...
    modelos_creados.inc()
    if exitoso:
        modelos_exitosos.inc()
    ingresos_generados.set(self.ingresos_totales)
```

---

## 📚 Guía de Desarrollo

### Agregar Nueva Estrategia

1. **Crear clase en `dominio/estrategias.py`**:
```python
class Estrategianueva(EstrategiaBase):
    async def ejecutar(self) -> float:
        # Implementar lógica
        return ingresos
```

2. **Registrar en agente**:
```python
# En dominio/agente.py
self.estrategias = [
    EstrategiaArbitraje(),
    EstrategiaTareasMicro(),
    EstrategiaDropshipping(),
    EstrategiaContenidoIA(),
    Estrategianueva()  # Nueva
]
```

3. **Agregar tests**:
```python
# En tests/test_estrategias.py
@pytest.mark.asyncio
async def test_estrategia_nueva():
    estrategia = Estrategianueva()
    ingresos = await estrategia.ejecutar()
    assert ingresos >= 0
```

---

## 🛠️ Comandos Útiles

### Desarrollo Local

```bash
# Clonar repositorio
git clone https://github.com/jikey8911/AutomataAiJeiKei.git
cd AutomataAiJeiKei

# Iniciar con Docker Compose (localhost)
docker-compose -f docker-compose-local.yml up -d

# Ver logs del agente
docker-compose logs -f automata_agente

# Acceder al dashboard
open http://localhost:8000

# Detener servicios
docker-compose down
```

### Base de Datos

```bash
# Conectar a PostgreSQL
docker exec -it automata_db psql -U automata -d automata_ai

# Ver modelos
SELECT * FROM modelos_ingresos;

# Ver base de conocimiento
SELECT * FROM base_conocimiento;

# Ver logs de decisión
SELECT * FROM logs_decision;
```

### Testing

```bash
# Tests de Python
pytest tests/ -v

# Tests de JavaScript
npm test

# Coverage
pytest --cov=backend tests/
```

### Despliegue en Oracle

```bash
# SSH a Oracle
ssh -i ~/.ssh/jeikei_oracle ubuntu@147.224.220.58

# Actualizar código
cd /home/ubuntu/AutomataAiJeiKei
git pull origin main

# Reiniciar servicios
docker-compose -f docker-compose-local.yml restart

# Ver estado
docker-compose ps
```

---

## 📊 Métricas de Éxito (Fase 3)

| Métrica | Target | Actual |
|---------|--------|--------|
| Ingresos generados | $1,000 USDT | $0 (MVP) |
| Modelos activos | 10+ | 0 (MVP) |
| Tasa de éxito | 30%+ | N/A (MVP) |
| Tiempo de ciclo | < 5 min | 5 min |
| Uptime | 99%+ | N/A (MVP) |
| Transferencias automáticas | Diarias | No implementado |

---

## 🔐 Seguridad

**Consideraciones Importantes**:

1. **API Keys de Binance**:
   - Nunca commitear en Git
   - Usar variables de entorno
   - Usar Testnet para desarrollo
   - Rotar keys regularmente

2. **Base de Datos**:
   - Cambiar contraseña default
   - Usar SSL en producción
   - Backups automáticos
   - Encriptar datos sensibles

3. **Autenticación**:
   - Implementar OAuth2 para dashboard
   - Rate limiting en API
   - Validación de entrada
   - Logging de accesos

---

## 📞 Soporte

**Problemas Comunes**:

1. **Puerto 11434 ya en uso**:
   ```bash
   sudo lsof -i :11434
   sudo kill -9 <PID>
   ```

2. **Base de datos no existe**:
   ```bash
   docker exec -u postgres automata_db psql -c "CREATE DATABASE automata_ai;"
   ```

3. **Ollama no responde**:
   ```bash
   docker-compose logs automata_ollama
   docker-compose restart automata_ollama
   ```

---

## 🎯 Próximos Pasos

1. ✅ Implementar Binance real
2. ✅ Crear estrategias reales
3. ✅ Configurar Appium
4. ✅ Agregar tests
5. ✅ Desplegar en producción
6. ✅ Monitorear 24/7
7. ✅ Alcanzar meta de $1,000

---

**Versión**: 3.0.0 (Fase 3)  
**Última Actualización**: 2026-03-26  
**Estado**: Listo para implementación  
**Repositorio**: https://github.com/jikey8911/AutomataAiJeiKei
