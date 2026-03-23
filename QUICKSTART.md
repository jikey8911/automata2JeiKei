# ⚡ Guía Rápida - AutomataAI

## 🎯 Inicio en 5 Minutos

### Requisitos

- Docker y Docker Compose instalados
- Puerto 8000 disponible

### Pasos

**1. Clonar el repositorio**

```bash
git clone https://github.com/jikey8911/AutomataAiJeiKei.git
cd AutomataAiJeiKei
```

**2. Iniciar los servicios**

```bash
docker-compose up --build
```

Espera a que todos los servicios estén saludables (verás mensajes de "healthy").

**3. Acceder al dashboard**

Abre tu navegador en: **http://localhost:8000**

Deberías ver el dashboard con tema oscuro y acentos neón verde.

**4. Iniciar el agente**

Haz clic en el botón **"INICIAR AGENTE"** en el dashboard.

Verás los logs en tiempo real mientras el agente:
- Investiga estrategias de monetización
- Formula hipótesis de negocio
- Ejecuta modelos
- Analiza resultados
- Adapta estrategias

---

## 📊 Qué Está Pasando

El dashboard muestra en tiempo real:

| Métrica | Descripción |
|---------|------------|
| **Ingresos Totales** | Dinero acumulado (simulado en MVP) |
| **Modelos Activos** | Estrategias en ejecución |
| **Modelos Exitosos** | Estrategias rentables (se duplican) |
| **Tasa de Éxito** | Porcentaje de modelos exitosos |
| **Pensamiento en Vivo** | Logs de cada decisión de la IA |

---

## 🔧 Troubleshooting

### El dashboard no carga

```bash
# Verificar que los servicios estén corriendo
docker-compose ps

# Ver logs del backend
docker-compose logs agente

# Reiniciar todo
docker-compose restart
```

### PostgreSQL no inicia

```bash
# Eliminar volumen y reiniciar
docker-compose down -v
docker-compose up --build
```

### Ollama tarda mucho en descargar modelos

Es normal la primera vez. Los modelos se descargan automáticamente (~2-4 GB).

```bash
# Ver progreso
docker-compose logs ollama
```

---

## 📁 Estructura Importante

```
backend/
├── main.py              ← Aplicación FastAPI
├── dominio/agente.py    ← Cerebro de la IA
├── adaptadores/         ← Conexiones con servicios externos
├── puertos/             ← Interfaces (contratos)
└── static/              ← Dashboard frontend
```

---

## 🚀 Próximos Pasos

1. **Explorar los logs** para entender cómo piensa la IA
2. **Leer `PROMPT_CONTINUACION.md`** para ver cómo agregar más funcionalidades
3. **Modificar estrategias** en `backend/dominio/agente.py` (método `_fase_investigacion`)

---

## 💡 Tips

- El ciclo del agente se ejecuta cada 5 minutos (configurable en `main.py`)
- Los ingresos en MVP son simulados (próxima fase: integración con Binance)
- Los logs se guardan en PostgreSQL para análisis histórico
- El dashboard se actualiza en tiempo real vía WebSocket

---

## 📞 Soporte

- **Documentación completa**: Ver `README.md`
- **Desarrollo futuro**: Ver `PROMPT_CONTINUACION.md`
- **Código fuente**: https://github.com/jikey8911/AutomataAiJeiKei

---

**¡Disfruta viendo a tu IA trabajar! 🤖✨**
