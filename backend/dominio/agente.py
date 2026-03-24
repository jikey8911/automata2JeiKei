import asyncio
import json
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from puertos.repositorio import IRepositorio, ModeloIngresos
from puertos.buscador import IBuscadorWeb
from puertos.lenguaje import IGeneradorDeLenguaje
from puertos.automatizador import IAutomatizadorUI
from puertos.financiero import IServicioFinanciero
from dominio.base_conocimiento import BaseDeConocimiento


class EstadoAgente(str, Enum):
    """Estados posibles del agente"""
    INVESTIGANDO = "INVESTIGANDO"
    FORMULANDO_HIPOTESIS = "FORMULANDO_HIPOTESIS"
    EJECUTANDO = "EJECUTANDO"
    ANALIZANDO = "ANALIZANDO"
    ADAPTANDO = "ADAPTANDO"
    DESCANSANDO = "DESCANSANDO"


class AgenteAutonomo:
    """El cerebro central del sistema de IA autónoma"""
    
    def __init__(
        self,
        repositorio: IRepositorio,
        buscador: IBuscadorWeb,
        generador_lenguaje: IGeneradorDeLenguaje,
        automatizador: Optional[IAutomatizadorUI] = None,
        servicio_financiero: Optional[IServicioFinanciero] = None
    ):
        self.repositorio = repositorio
        self.buscador = buscador
        self.generador_lenguaje = generador_lenguaje
        self.automatizador = automatizador
        self.servicio_financiero = servicio_financiero
        self.base_conocimiento = BaseDeConocimiento()
        
        self.estado_actual = EstadoAgente.DESCANSANDO
        self.ciclos_completados = 0
        self.ingresos_totales = 0.0
        self.modelos_activos: List[ModeloIngresos] = []
        
        # Callbacks para comunicación con el dashboard
        self.callbacks_estado = []
        self.callbacks_log = []
    
    def registrar_callback_estado(self, callback):
        """Registrar callback para cambios de estado"""
        self.callbacks_estado.append(callback)
    
    def registrar_callback_log(self, callback):
        """Registrar callback para logs de decisión"""
        self.callbacks_log.append(callback)
    
    async def emitir_estado(self, datos: Dict[str, Any]) -> None:
        """Emitir cambio de estado a todos los callbacks"""
        for callback in self.callbacks_estado:
            try:
                await callback(datos)
            except Exception as e:
                print(f"Error en callback de estado: {e}")
    
    async def emitir_log(self, log_data: Dict[str, Any]) -> None:
        """Emitir log de decisión a todos los callbacks"""
        for callback in self.callbacks_log:
            try:
                await callback(log_data)
            except Exception as e:
                print(f"Error en callback de log: {e}")
    
    async def ejecutar_ciclo(self) -> None:
        """Ejecutar un ciclo completo de investigación -> hipótesis -> ejecución -> análisis"""
        try:
            self.ciclos_completados += 1
            
            # Fase 1: INVESTIGACIÓN
            await self._fase_investigacion()
            
            # Fase 2: FORMULACIÓN DE HIPÓTESIS
            await self._fase_formulacion_hipotesis()
            
            # Fase 3: EJECUCIÓN (Simulada en MVP)
            await self._fase_ejecucion()
            
            # Fase 4: ANÁLISIS
            await self._fase_analisis()
            
            # Fase 5: ADAPTACIÓN
            await self._fase_adaptacion()
            
            # Actualizar estado general
            await self._actualizar_estado_general()
            
        except Exception as e:
            print(f"Error en ciclo del agente: {e}")
            await self.emitir_log({
                "timestamp": datetime.now().isoformat(),
                "estado_agente": "ERROR",
                "mensaje": str(e)
            })
    
    async def _fase_investigacion(self) -> None:
        """Fase 1: Investigar nuevas estrategias de monetización"""
        self.estado_actual = EstadoAgente.INVESTIGANDO
        
        await self.emitir_log({
            "timestamp": datetime.now().isoformat(),
            "estado_agente": self.estado_actual,
            "mensaje": "Iniciando investigación de estrategias de monetización..."
        })
        
        # Búsquedas de investigación
        queries = [
            "nuevas formas de generar ingresos con IA 2026",
            "monetización de contenido viral TikTok",
            "freelancing automatizado con inteligencia artificial",
            "marketing de afiliados rentable",
            "passive income con APIs"
        ]
        
        for query in queries:
            try:
                resultados = await self.buscador.buscar(query, num_resultados=5)
                
                # Guardar conocimiento de los resultados
                for resultado in resultados:
                    self.base_conocimiento.agregar_conocimiento(
                        tipo="estrategia_exitosa",
                        contenido={
                            "titulo": resultado.titulo,
                            "url": resultado.url,
                            "descripcion": resultado.descripcion,
                            "query": query
                        },
                        relevancia=resultado.relevancia
                    )
                
                await self.emitir_log({
                    "timestamp": datetime.now().isoformat(),
                    "estado_agente": self.estado_actual,
                    "mensaje": f"Búsqueda completada: '{query}' - {len(resultados)} resultados encontrados"
                })
                
            except Exception as e:
                print(f"Error en búsqueda: {e}")
    
    async def _fase_formulacion_hipotesis(self) -> None:
        """Fase 2: Formular hipótesis de negocio basadas en investigación"""
        self.estado_actual = EstadoAgente.FORMULANDO_HIPOTESIS
        
        await self.emitir_log({
            "timestamp": datetime.now().isoformat(),
            "estado_agente": self.estado_actual,
            "mensaje": "Formulando hipótesis de negocio..."
        })
        
        # Obtener conocimiento relevante
        estrategias = self.base_conocimiento.obtener_mas_relevante("estrategia_exitosa", limite=3)
        
        if not estrategias:
            await self.emitir_log({
                "timestamp": datetime.now().isoformat(),
                "estado_agente": self.estado_actual,
                "mensaje": "No hay suficiente conocimiento para formular hipótesis"
            })
            return
        
        # Construir contexto para el LLM
        contexto_estrategias = "\n".join([
            f"- {item.contenido.get('titulo', 'Sin título')}: {item.contenido.get('descripcion', '')}"
            for item in estrategias
        ])
        
        prompt = f"""Basándote en estas estrategias de monetización investigadas:

{contexto_estrategias}

Genera una hipótesis de negocio innovadora y viable para generar ingresos en línea.
La hipótesis debe incluir:
1. Nombre de la estrategia
2. Descripción breve
3. Pasos de ejecución
4. Métrica de éxito (KPI)
5. Tiempo estimado para primeros ingresos

Responde en formato JSON."""
        
        try:
            respuesta = await self.generador_lenguaje.generar_texto(
                prompt=prompt,
                modelo_preferido="mixtral",
                temperatura=0.8,
                max_tokens=1500
            )
            
            # Parsear respuesta JSON
            try:
                hipotesis_data = json.loads(respuesta)
            except json.JSONDecodeError:
                # Si no es JSON válido, crear una estructura por defecto
                hipotesis_data = {
                    "nombre": "Estrategia Experimental",
                    "descripcion": respuesta[:200],
                    "pasos": ["Paso 1", "Paso 2", "Paso 3"],
                    "kpi": "Ingresos generados",
                    "tiempo_estimado": "7 días"
                }
            
            # Crear nuevo modelo de ingresos
            nuevo_modelo = ModeloIngresos(
                id=uuid4(),
                estrategia_nombre=hipotesis_data.get("nombre", "Estrategia Experimental"),
                estado="activo",
                descripcion=hipotesis_data.get("descripcion", ""),
                plan_ejecucion=hipotesis_data
            )
            
            # Guardar en repositorio
            await self.repositorio.guardar_modelo(nuevo_modelo)
            self.modelos_activos.append(nuevo_modelo)
            
            await self.emitir_log({
                "timestamp": datetime.now().isoformat(),
                "estado_agente": self.estado_actual,
                "mensaje": f"Hipótesis creada: {nuevo_modelo.estrategia_nombre}",
                "modelo_id": str(nuevo_modelo.id)
            })
            
        except Exception as e:
            print(f"Error al generar hipótesis: {e}")
            await self.emitir_log({
                "timestamp": datetime.now().isoformat(),
                "estado_agente": self.estado_actual,
                "mensaje": f"Error al generar hipótesis: {str(e)}"
            })
    
    async def _fase_ejecucion(self) -> None:
        """Fase 3: Ejecutar los modelos (Simulada en MVP)"""
        self.estado_actual = EstadoAgente.EJECUTANDO
        
        await self.emitir_log({
            "timestamp": datetime.now().isoformat(),
            "estado_agente": self.estado_actual,
            "mensaje": "Iniciando ejecución de modelos..."
        })
        
        for modelo in self.modelos_activos:
            if modelo.estado == "activo":
                # En MVP, simulamos la ejecución
                plan = modelo.plan_ejecucion
                pasos = plan.get("pasos", [])
                
                for paso in pasos:
                    await self.emitir_log({
                        "timestamp": datetime.now().isoformat(),
                        "estado_agente": self.estado_actual,
                        "mensaje": f"[{modelo.estrategia_nombre}] Ejecutando: {paso}",
                        "modelo_id": str(modelo.id)
                    })
                    await asyncio.sleep(0.5)  # Simular trabajo
    
    async def _fase_analisis(self) -> None:
        """Fase 4: Analizar resultados de los modelos"""
        self.estado_actual = EstadoAgente.ANALIZANDO
        
        await self.emitir_log({
            "timestamp": datetime.now().isoformat(),
            "estado_agente": self.estado_actual,
            "mensaje": "Analizando resultados de modelos..."
        })
        
        for modelo in self.modelos_activos:
            # Simular análisis: 60% de probabilidad de éxito
            import random
            exito = random.random() > 0.4
            
            if exito:
                # Simular ingresos generados
                ingresos_simulados = random.uniform(10, 100)
                modelo.ingresos_generados = ingresos_simulados
                modelo.estado = "exitoso"
                self.ingresos_totales += ingresos_simulados
                
                await self.repositorio.actualizar_estado_modelo(modelo.id, "exitoso")
                await self.repositorio.actualizar_ingresos_modelo(modelo.id, ingresos_simulados)
                
                await self.emitir_log({
                    "timestamp": datetime.now().isoformat(),
                    "estado_agente": self.estado_actual,
                    "mensaje": f"✓ {modelo.estrategia_nombre}: EXITOSO - ${ingresos_simulados:.2f} generados",
                    "modelo_id": str(modelo.id)
                })
            else:
                modelo.estado = "fallido"
                await self.repositorio.actualizar_estado_modelo(modelo.id, "fallido")
                
                await self.emitir_log({
                    "timestamp": datetime.now().isoformat(),
                    "estado_agente": self.estado_actual,
                    "mensaje": f"✗ {modelo.estrategia_nombre}: FALLIDO - No generó ingresos",
                    "modelo_id": str(modelo.id)
                })
    
    async def _fase_adaptacion(self) -> None:
        """Fase 5: Adaptar estrategia basada en resultados"""
        self.estado_actual = EstadoAgente.ADAPTANDO
        
        await self.emitir_log({
            "timestamp": datetime.now().isoformat(),
            "estado_agente": self.estado_actual,
            "mensaje": "Adaptando estrategias basadas en resultados..."
        })
        
        # Duplicar modelos exitosos
        modelos_exitosos = [m for m in self.modelos_activos if m.estado == "exitoso"]
        
        for modelo_exitoso in modelos_exitosos:
            # Crear una copia del modelo exitoso
            nuevo_modelo = ModeloIngresos(
                id=uuid4(),
                estrategia_nombre=f"{modelo_exitoso.estrategia_nombre} (Duplicado)",
                estado="activo",
                descripcion=modelo_exitoso.descripcion,
                plan_ejecucion=modelo_exitoso.plan_ejecucion,
                modelo_padre_id=modelo_exitoso.id
            )
            
            await self.repositorio.guardar_modelo(nuevo_modelo)
            self.modelos_activos.append(nuevo_modelo)
            
            await self.emitir_log({
                "timestamp": datetime.now().isoformat(),
                "estado_agente": self.estado_actual,
                "mensaje": f"Modelo duplicado: {nuevo_modelo.estrategia_nombre}",
                "modelo_id": str(nuevo_modelo.id)
            })
        
        # Limpiar modelos fallidos
        self.modelos_activos = [m for m in self.modelos_activos if m.estado != "fallido"]
    
    async def _actualizar_estado_general(self) -> None:
        """Actualizar el estado general del agente en la BD"""
        modelos_activos = len([m for m in self.modelos_activos if m.estado == "activo"])
        modelos_exitosos = len([m for m in self.modelos_activos if m.estado == "exitoso"])
        modelos_fallidos = len([m for m in self.modelos_activos if m.estado == "fallido"])
        
        tasa_exito = modelos_exitosos / (modelos_exitosos + modelos_fallidos) if (modelos_exitosos + modelos_fallidos) > 0 else 0
        
        await self.repositorio.actualizar_estado_agente({
            "estado_actual": self.estado_actual.value,
            "ingresos_totales": self.ingresos_totales,
            "modelos_activos": modelos_activos,
            "modelos_exitosos": modelos_exitosos,
            "modelos_fallidos": modelos_fallidos,
            "tasa_exito": tasa_exito,
            "ciclos_completados": self.ciclos_completados
        })
        
        await self.emitir_estado({
            "timestamp": datetime.now().isoformat(),
            "estado_actual": self.estado_actual.value,
            "ingresos_totales": self.ingresos_totales,
            "modelos_activos": modelos_activos,
            "modelos_exitosos": modelos_exitosos,
            "modelos_fallidos": modelos_fallidos,
            "tasa_exito": round(tasa_exito * 100, 2),
            "ciclos_completados": self.ciclos_completados
        })
