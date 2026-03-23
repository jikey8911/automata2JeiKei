import json
import httpx
from typing import Optional

from puertos.lenguaje import IGeneradorDeLenguaje


class OllamaAdapter(IGeneradorDeLenguaje):
    """Adaptador para LLMs locales usando Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
        
        # Modelos disponibles en Ollama
        self.modelos_disponibles = {
            "phi-3": "phi-3",
            "mixtral": "mixtral",
            "llama2": "llama2",
            "neural-chat": "neural-chat"
        }
    
    async def _descargar_modelo_si_es_necesario(self, nombre_modelo: str) -> bool:
        """Verificar si el modelo está disponible, si no, descargarlo"""
        try:
            # Intentar obtener lista de modelos
            response = await self.client.get(f"{self.base_url}/api/tags")
            
            if response.status_code == 200:
                modelos = response.json().get("models", [])
                modelos_names = [m.get("name", "").split(":")[0] for m in modelos]
                
                if nombre_modelo not in modelos_names:
                    print(f"Descargando modelo {nombre_modelo}...")
                    # Descargar modelo
                    await self.client.post(
                        f"{self.base_url}/api/pull",
                        json={"name": nombre_modelo}
                    )
                    print(f"Modelo {nombre_modelo} descargado")
            
            return True
        except Exception as e:
            print(f"Error al verificar/descargar modelo: {e}")
            return False
    
    async def generar_texto(
        self,
        prompt: str,
        modelo_preferido: str = "phi-3",
        temperatura: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generar texto usando un LLM local en Ollama"""
        try:
            # Mapear nombre preferido al nombre real del modelo
            modelo = self.modelos_disponibles.get(modelo_preferido, "phi-3")
            
            # Asegurar que el modelo esté disponible
            await self._descargar_modelo_si_es_necesario(modelo)
            
            # Realizar llamada a Ollama
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": modelo,
                    "prompt": prompt,
                    "temperature": temperatura,
                    "num_predict": max_tokens,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                resultado = response.json()
                return resultado.get("response", "")
            else:
                print(f"Error en Ollama: {response.status_code}")
                return ""
        
        except Exception as e:
            print(f"Error al generar texto: {e}")
            return ""
    
    async def analizar_sentimiento(self, texto: str) -> dict:
        """Analizar el sentimiento de un texto"""
        prompt = f"""Analiza el sentimiento del siguiente texto y responde en JSON:
        
Texto: {texto}

Responde con un JSON que contenga:
- sentimiento: "positivo", "negativo" o "neutral"
- puntuacion: número entre -1 (muy negativo) y 1 (muy positivo)
- explicacion: breve explicación

Solo responde con el JSON, sin explicaciones adicionales."""
        
        try:
            respuesta = await self.generar_texto(
                prompt=prompt,
                modelo_preferido="phi-3",
                temperatura=0.3,
                max_tokens=200
            )
            
            # Parsear JSON
            try:
                resultado = json.loads(respuesta)
            except json.JSONDecodeError:
                resultado = {
                    "sentimiento": "neutral",
                    "puntuacion": 0.0,
                    "explicacion": "No se pudo analizar"
                }
            
            return resultado
        
        except Exception as e:
            print(f"Error al analizar sentimiento: {e}")
            return {"sentimiento": "error", "puntuacion": 0.0}
    
    async def extraer_entidades(self, texto: str) -> dict:
        """Extraer entidades nombradas de un texto"""
        prompt = f"""Extrae las entidades nombradas del siguiente texto y responde en JSON:

Texto: {texto}

Responde con un JSON que contenga:
- personas: lista de nombres de personas
- lugares: lista de nombres de lugares
- organizaciones: lista de nombres de organizaciones
- otros: lista de otras entidades importantes

Solo responde con el JSON, sin explicaciones adicionales."""
        
        try:
            respuesta = await self.generar_texto(
                prompt=prompt,
                modelo_preferido="phi-3",
                temperatura=0.3,
                max_tokens=300
            )
            
            try:
                resultado = json.loads(respuesta)
            except json.JSONDecodeError:
                resultado = {
                    "personas": [],
                    "lugares": [],
                    "organizaciones": [],
                    "otros": []
                }
            
            return resultado
        
        except Exception as e:
            print(f"Error al extraer entidades: {e}")
            return {"personas": [], "lugares": [], "organizaciones": [], "otros": []}
    
    async def generar_hipotesis(
        self,
        contexto: str,
        conocimiento_previo: str = ""
    ) -> dict:
        """Generar una hipótesis de negocio basada en contexto"""
        prompt = f"""Basándote en el siguiente contexto y conocimiento previo, genera una hipótesis de negocio innovadora para generar ingresos en línea.

CONTEXTO:
{contexto}

CONOCIMIENTO PREVIO:
{conocimiento_previo if conocimiento_previo else "Sin conocimiento previo"}

Genera una respuesta en JSON con:
- nombre: nombre de la estrategia
- descripcion: descripción breve (máx 200 caracteres)
- pasos: lista de 3-5 pasos de ejecución
- kpi: métrica de éxito principal
- tiempo_estimado: tiempo estimado para primeros ingresos
- riesgo: nivel de riesgo (bajo, medio, alto)
- potencial_ingresos: estimación de ingresos potenciales

Solo responde con el JSON, sin explicaciones adicionales."""
        
        try:
            respuesta = await self.generar_texto(
                prompt=prompt,
                modelo_preferido="mixtral",
                temperatura=0.8,
                max_tokens=1500
            )
            
            try:
                resultado = json.loads(respuesta)
            except json.JSONDecodeError:
                resultado = {
                    "nombre": "Estrategia Experimental",
                    "descripcion": "Hipótesis generada",
                    "pasos": ["Paso 1", "Paso 2", "Paso 3"],
                    "kpi": "Ingresos generados",
                    "tiempo_estimado": "7 días",
                    "riesgo": "medio",
                    "potencial_ingresos": "$100-500"
                }
            
            return resultado
        
        except Exception as e:
            print(f"Error al generar hipótesis: {e}")
            return {"error": str(e)}
    
    async def evaluar_viabilidad(
        self,
        estrategia: str,
        restricciones: str = ""
    ) -> dict:
        """Evaluar la viabilidad de una estrategia"""
        prompt = f"""Evalúa la viabilidad de la siguiente estrategia de negocio:

ESTRATEGIA:
{estrategia}

RESTRICCIONES:
{restricciones if restricciones else "Sin restricciones específicas"}

Proporciona un análisis en JSON con:
- viabilidad: puntuación de 0-100
- fortalezas: lista de fortalezas
- debilidades: lista de debilidades
- oportunidades: lista de oportunidades
- amenazas: lista de amenazas
- recomendacion: "proceder", "revisar" o "descartar"
- justificacion: breve justificación

Solo responde con el JSON, sin explicaciones adicionales."""
        
        try:
            respuesta = await self.generar_texto(
                prompt=prompt,
                modelo_preferido="mixtral",
                temperatura=0.5,
                max_tokens=1500
            )
            
            try:
                resultado = json.loads(respuesta)
            except json.JSONDecodeError:
                resultado = {
                    "viabilidad": 50,
                    "fortalezas": [],
                    "debilidades": [],
                    "oportunidades": [],
                    "amenazas": [],
                    "recomendacion": "revisar",
                    "justificacion": "Análisis no disponible"
                }
            
            return resultado
        
        except Exception as e:
            print(f"Error al evaluar viabilidad: {e}")
            return {"viabilidad": 0, "error": str(e)}
