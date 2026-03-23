# 🤖 AutomataAI - Agente Autónomo de Generación de Ingresos

Un sistema de inteligencia artificial autónomo que genera ingresos 24/7 mediante investigación, formulación de hipótesis, ejecución de modelos y adaptación continua. Utiliza **Arquitectura Hexagonal**, **LLMs locales con Ollama** y un **dashboard en tiempo real** con estilo **jeikei-design-system**.

## 🎯 Características del MVP

- **Núcleo Hexagonal**: Arquitectura limpia y modular con puertos y adaptadores
- **Agente Autónomo**: Ciclo continuo de investigación → hipótesis → ejecución → análisis → adaptación
- **LLMs Locales**: Integración con Ollama (Llama 3, Mixtral, Phi-3) sin costo de tokens
- **Persistencia PostgreSQL**: Almacenamiento de modelos, conocimiento y logs de decisión
- **WebSocket en Tiempo Real**: Dashboard con logs de pensamiento de la IA en vivo
- **Búsqueda Web Gratuita**: DuckDuckGo API para investigación autónoma
- **Interfaz Futurista**: Dashboard estilo jeikei-design-system con tema oscuro y acentos neón

## 📁 Estructura del Proyecto

```
AutomataAiJeiKei/
├── backend/
│   ├── adaptadores/           # Implementaciones de puertos
│   │   ├── postgres_adapter.py
│   │   ├── duckduckgo_adapter.py
│   │   └── ollama_adapter.py
│   ├── dominio/               # Lógica de negocio (núcleo)
│   │   ├── agente.py
│   │   └── base_conocimiento.py
│   ├── puertos/               # Interfaces/contratos
│   │   ├── repositorio.py
│   │   ├── buscador.py
│   │   └── lenguaje.py
│   ├── static/                # Frontend estático
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   ├── main.py                # Aplicación FastAPI
│   ├── requirements.txt        # Dependencias Python
│   ├── Dockerfile
│   └── init.sql               # Esquema de base de datos
├── docker-compose.yml         # Orquestación de servicios
└── README.md
```

## 🚀 Inicio Rápido

### Requisitos Previos

- Docker y Docker Compose instalados
- (Opcional) NVIDIA GPU con drivers CUDA para acelerar Ollama

### Pasos de Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/jikey8911/AutomataAiJeiKei.git
cd AutomataAiJeiKei
```

2. **Iniciar los servicios con Docker Compose**:
```bash
docker-compose up --build
```

Esto iniciará:
- **PostgreSQL** en puerto 5432
- **Ollama** en puerto 11434
- **FastAPI Backend** en puerto 8000

3. **Acceder al dashboard**:
Abre tu navegador en `http://localhost:8000`

## 🔧 Configuración

### Variables de Entorno

Edita `docker-compose.yml` para personalizar:

```yaml
environment:
  DATABASE_URL: postgresql://automata:automata_secure_password@db:5432/automata_ai
  OLLAMA_BASE_URL: http://ollama:11434
```

### Modelos de Ollama

Los modelos se descargan automáticamente la primera vez. Para pre-descargar:

```bash
docker exec automata_ollama ollama pull llama2
docker exec automata_ollama ollama pull mixtral
docker exec automata_ollama ollama pull phi-3
```

## 📊 API Endpoints

### REST API

- `GET /api/health` - Verificar salud del servidor
- `GET /api/status` - Obtener estado actual del agente y KPIs
- `GET /api/modelos?estado=activo` - Listar modelos de ingresos
- `POST /api/control` - Controlar el agente (iniciar/pausar/reanudar)

### WebSocket

- `WS /ws/logs` - Conexión en tiempo real para logs y cambios de estado

## 🏗️ Arquitectura Hexagonal

### Puertos (Interfaces)

| Puerto | Responsabilidad |
|--------|-----------------|
| `IRepositorio` | Persistencia de datos |
| `IBuscadorWeb` | Búsqueda en internet |
| `IGeneradorDeLenguaje` | Generación de texto con LLMs |

### Adaptadores

| Adaptador | Implementa | Tecnología |
|-----------|-----------|-----------|
| `PostgresAdapter` | `IRepositorio` | PostgreSQL |
| `DuckDuckGoAdapter` | `IBuscadorWeb` | DuckDuckGo Search |
| `OllamaAdapter` | `IGeneradorDeLenguaje` | Ollama |

### Dominio (Núcleo)

- `AgenteAutonomo`: Orquesta el ciclo completo
- `BaseDeConocimiento`: Almacena aprendizajes
- `ModeloIngresos`: Representa un experimento

## 🔄 Ciclo de Vida del Agente

```
1. INVESTIGACIÓN
   ↓
   Busca estrategias de monetización en internet
   ↓
2. FORMULACIÓN DE HIPÓTESIS
   ↓
   Usa LLM para crear hipótesis de negocio
   ↓
3. EJECUCIÓN
   ↓
   Ejecuta el plan (simulado en MVP)
   ↓
4. ANÁLISIS
   ↓
   Analiza resultados y marca como exitoso/fallido
   ↓
5. ADAPTACIÓN
   ↓
   Duplica modelos exitosos, elimina fallidos
   ↓
   [Vuelve a INVESTIGACIÓN]
```

## 📈 Dashboard

El dashboard muestra en tiempo real:

- **KPIs**: Ingresos totales, modelos activos/exitosos/fallidos, tasa de éxito
- **Pensamiento en Vivo**: Logs de cada decisión del agente
- **Estadísticas de Modelos**: Contador de modelos por estado
- **Controles**: Botones para iniciar/pausar el agente

## 🔮 Fase 2: Desarrollo Completo (Próximos Pasos)

Ver `PROMPT_CONTINUACION.md` para instrucciones detalladas sobre:

1. **Adaptador de Android Virtual** (Appium)
2. **Integración de Pagos** (Binance API)
3. **Dashboard Avanzado** (SvelteKit + Tailwind)
4. **Ejecución Real** (Automatización de acciones)
5. **Sistema de Ciclo de Vida** (Completo)

## 🛠️ Desarrollo Local

### Instalar dependencias

```bash
cd backend
pip install -r requirements.txt
```

### Ejecutar sin Docker

```bash
# Terminal 1: PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:16-alpine

# Terminal 2: Ollama
docker run -d -p 11434:11434 ollama/ollama

# Terminal 3: Backend
export DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
python -m uvicorn main:app --reload
```

## 📝 Logs y Debugging

Los logs se almacenan en PostgreSQL en la tabla `logs_decision`:

```sql
SELECT timestamp, estado_agente, decision_tomada 
FROM logs_decision 
ORDER BY timestamp DESC 
LIMIT 10;
```

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- **jeikei-design-system** por el sistema de diseño futurista
- **Ollama** por facilitar LLMs locales
- **FastAPI** por el framework web moderno
- **DuckDuckGo** por la API de búsqueda gratuita

---

**Desarrollado con ❤️ por AutomataAI**

*"La inteligencia autónoma que genera ingresos mientras duermes"* 🚀
