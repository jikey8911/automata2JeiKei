import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import create_engine, text, select, update
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from puertos.repositorio import IRepositorio, ModeloIngresos


class PostgresAdapter(IRepositorio):
    """Adaptador para persistencia en PostgreSQL"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            poolclass=NullPool,
            echo=False
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _get_session(self) -> Session:
        """Obtener una sesión de base de datos"""
        return self.SessionLocal()
    
    async def guardar_modelo(self, modelo: ModeloIngresos) -> None:
        """Guardar un modelo de ingresos"""
        session = self._get_session()
        try:
            query = text("""
                INSERT INTO modelos_ingresos 
                (id, estrategia_nombre, estado, ingresos_generados, fecha_creacion, 
                 datos_metricas, descripcion, plan_ejecucion, modelo_padre_id)
                VALUES (:id, :estrategia_nombre, :estado, :ingresos_generados, :fecha_creacion,
                        :datos_metricas, :descripcion, :plan_ejecucion, :modelo_padre_id)
                ON CONFLICT (id) DO UPDATE SET
                    estado = EXCLUDED.estado,
                    ingresos_generados = EXCLUDED.ingresos_generados,
                    datos_metricas = EXCLUDED.datos_metricas,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            """)
            
            session.execute(query, {
                "id": str(modelo.id),
                "estrategia_nombre": modelo.estrategia_nombre,
                "estado": modelo.estado,
                "ingresos_generados": modelo.ingresos_generados,
                "fecha_creacion": modelo.fecha_creacion,
                "datos_metricas": json.dumps(modelo.datos_metricas),
                "descripcion": modelo.descripcion,
                "plan_ejecucion": json.dumps(modelo.plan_ejecucion),
                "modelo_padre_id": str(modelo.modelo_padre_id) if modelo.modelo_padre_id else None
            })
            session.commit()
        finally:
            session.close()
    
    async def actualizar_estado_modelo(self, modelo_id: UUID, nuevo_estado: str) -> None:
        """Actualizar el estado de un modelo"""
        session = self._get_session()
        try:
            query = text("""
                UPDATE modelos_ingresos 
                SET estado = :estado, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = :id
            """)
            session.execute(query, {"estado": nuevo_estado, "id": str(modelo_id)})
            session.commit()
        finally:
            session.close()
    
    async def obtener_modelo(self, modelo_id: UUID) -> Optional[ModeloIngresos]:
        """Obtener un modelo por ID"""
        session = self._get_session()
        try:
            query = text("SELECT * FROM modelos_ingresos WHERE id = :id")
            result = session.execute(query, {"id": str(modelo_id)}).fetchone()
            
            if result:
                return self._row_to_modelo(result)
            return None
        finally:
            session.close()
    
    async def obtener_todos_modelos(self, estado: Optional[str] = None) -> List[ModeloIngresos]:
        """Obtener todos los modelos"""
        session = self._get_session()
        try:
            if estado:
                query = text("SELECT * FROM modelos_ingresos WHERE estado = :estado ORDER BY fecha_creacion DESC")
                results = session.execute(query, {"estado": estado}).fetchall()
            else:
                query = text("SELECT * FROM modelos_ingresos ORDER BY fecha_creacion DESC")
                results = session.execute(query).fetchall()
            
            return [self._row_to_modelo(row) for row in results]
        finally:
            session.close()
    
    async def actualizar_ingresos_modelo(self, modelo_id: UUID, ingresos: float) -> None:
        """Actualizar los ingresos de un modelo"""
        session = self._get_session()
        try:
            query = text("""
                UPDATE modelos_ingresos 
                SET ingresos_generados = :ingresos, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = :id
            """)
            session.execute(query, {"ingresos": ingresos, "id": str(modelo_id)})
            session.commit()
        finally:
            session.close()
    
    async def guardar_conocimiento(self, tipo: str, contenido: Dict[str, Any], relevancia: float = 0.5) -> None:
        """Guardar un nuevo conocimiento"""
        session = self._get_session()
        try:
            query = text("""
                INSERT INTO base_conocimiento (tipo_conocimiento, contenido, relevancia)
                VALUES (:tipo, :contenido, :relevancia)
            """)
            session.execute(query, {
                "tipo": tipo,
                "contenido": json.dumps(contenido),
                "relevancia": relevancia
            })
            session.commit()
        finally:
            session.close()
    
    async def obtener_conocimiento(self, tipo: str) -> List[Dict[str, Any]]:
        """Obtener conocimiento por tipo"""
        session = self._get_session()
        try:
            query = text("""
                SELECT id, tipo_conocimiento, contenido, relevancia, fecha_aprendizaje
                FROM base_conocimiento
                WHERE tipo_conocimiento = :tipo
                ORDER BY relevancia DESC
            """)
            results = session.execute(query, {"tipo": tipo}).fetchall()
            
            return [
                {
                    "id": row[0],
                    "tipo": row[1],
                    "contenido": json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    "relevancia": float(row[3]),
                    "fecha_aprendizaje": row[4]
                }
                for row in results
            ]
        finally:
            session.close()
    
    async def guardar_log_decision(
        self,
        estado_agente: str,
        prompt_enviado: str,
        respuesta_recibida: str,
        decision_tomada: str,
        modelo_id: Optional[UUID] = None,
        nivel_confianza: float = 0.5
    ) -> None:
        """Guardar un log de decisión"""
        session = self._get_session()
        try:
            query = text("""
                INSERT INTO logs_decision 
                (estado_agente, prompt_enviado, respuesta_recibida, decision_tomada, 
                 modelo_id_relacionado, nivel_confianza)
                VALUES (:estado_agente, :prompt_enviado, :respuesta_recibida, :decision_tomada,
                        :modelo_id, :nivel_confianza)
            """)
            session.execute(query, {
                "estado_agente": estado_agente,
                "prompt_enviado": prompt_enviado,
                "respuesta_recibida": respuesta_recibida,
                "decision_tomada": decision_tomada,
                "modelo_id": str(modelo_id) if modelo_id else None,
                "nivel_confianza": nivel_confianza
            })
            session.commit()
        finally:
            session.close()
    
    async def obtener_estado_agente(self) -> Dict[str, Any]:
        """Obtener el estado actual del agente"""
        session = self._get_session()
        try:
            query = text("""
                SELECT estado_actual, ingresos_totales, ingresos_semana_actual,
                       modelos_activos, modelos_exitosos, modelos_fallidos,
                       tasa_exito, ciclos_completados
                FROM estado_agente
                ORDER BY fecha_actualizacion DESC
                LIMIT 1
            """)
            result = session.execute(query).fetchone()
            
            if result:
                return {
                    "estado_actual": result[0],
                    "ingresos_totales": float(result[1]),
                    "ingresos_semana_actual": float(result[2]),
                    "modelos_activos": result[3],
                    "modelos_exitosos": result[4],
                    "modelos_fallidos": result[5],
                    "tasa_exito": float(result[6]),
                    "ciclos_completados": result[7]
                }
            return {}
        finally:
            session.close()
    
    async def actualizar_estado_agente(self, datos: Dict[str, Any]) -> None:
        """Actualizar el estado del agente"""
        session = self._get_session()
        try:
            query = text("""
                UPDATE estado_agente
                SET estado_actual = :estado_actual,
                    ingresos_totales = :ingresos_totales,
                    modelos_activos = :modelos_activos,
                    modelos_exitosos = :modelos_exitosos,
                    modelos_fallidos = :modelos_fallidos,
                    tasa_exito = :tasa_exito,
                    ciclos_completados = :ciclos_completados,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = (SELECT id FROM estado_agente LIMIT 1)
            """)
            session.execute(query, {
                "estado_actual": datos.get("estado_actual", "ACTIVO"),
                "ingresos_totales": datos.get("ingresos_totales", 0),
                "modelos_activos": datos.get("modelos_activos", 0),
                "modelos_exitosos": datos.get("modelos_exitosos", 0),
                "modelos_fallidos": datos.get("modelos_fallidos", 0),
                "tasa_exito": datos.get("tasa_exito", 0),
                "ciclos_completados": datos.get("ciclos_completados", 0)
            })
            session.commit()
        finally:
            session.close()
    
    def _row_to_modelo(self, row) -> ModeloIngresos:
        """Convertir una fila de BD a objeto ModeloIngresos"""
        return ModeloIngresos(
            id=UUID(row[0]) if isinstance(row[0], str) else row[0],
            estrategia_nombre=row[1],
            estado=row[2],
            ingresos_generados=float(row[3]),
            fecha_creacion=row[4],
            datos_metricas=json.loads(row[5]) if isinstance(row[5], str) else row[5],
            descripcion=row[6] or "",
            plan_ejecucion=json.loads(row[7]) if isinstance(row[7], str) else row[7],
            modelo_padre_id=UUID(row[8]) if row[8] else None
        )

    async def guardar_configuracion_binance(self, config: Dict[str, Any]) -> None:
        """Guardar configuración de Binance con encripción"""
        from utils.security import encrypt_data
        session = self._get_session()
        try:
            query = text("""
                INSERT INTO binance_integrations (api_key_enc, api_secret_enc, direccion_usdt, testnet)
                VALUES (:key, :secret, :addr, :testnet)
                ON CONFLICT (id) DO UPDATE SET
                    api_key_enc = EXCLUDED.api_key_enc,
                    api_secret_enc = EXCLUDED.api_secret_enc,
                    direccion_usdt = EXCLUDED.direccion_usdt,
                    testnet = EXCLUDED.testnet,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            """)
            session.execute(query, {
                "key": encrypt_data(config['api_key']),
                "secret": encrypt_data(config['api_secret']),
                "addr": config.get('direccion_usdt'),
                "testnet": config.get('testnet', False)
            })
            session.commit()
        finally:
            session.close()

    async def obtener_configuracion_binance(self) -> Optional[Dict[str, Any]]:
        """Obtener y desencriptar configuración de Binance"""
        from utils.security import decrypt_data
        session = self._get_session()
        try:
            query = text("SELECT api_key_enc, api_secret_enc, direccion_usdt, testnet FROM binance_integrations LIMIT 1")
            result = session.execute(query).fetchone()
            if result:
                return {
                    "api_key": decrypt_data(result[0]),
                    "api_secret": decrypt_data(result[1]),
                    "direccion_usdt": result[2],
                    "testnet": result[3]
                }
            return None
        finally:
            session.close()

    async def guardar_configuracion_comodolar(self, config: Dict[str, Any]) -> None:
        """Guardar configuración de Comodolar/DolarApp con encripción"""
        from utils.security import encrypt_data
        session = self._get_session()
        try:
            query = text("""
                INSERT INTO comodolar_integrations (api_key_enc, api_secret_enc, api_url)
                VALUES (:key, :secret, :url)
                ON CONFLICT (id) DO UPDATE SET
                    api_key_enc = EXCLUDED.api_key_enc,
                    api_secret_enc = EXCLUDED.api_secret_enc,
                    api_url = EXCLUDED.api_url,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            """)
            session.execute(query, {
                "key": encrypt_data(config['api_key']),
                "secret": encrypt_data(config['api_secret']),
                "url": config.get('api_url', 'http://dolarapp-backend:8000')
            })
            session.commit()
        finally:
            session.close()

    async def obtener_configuracion_comodolar(self) -> Optional[Dict[str, Any]]:
        """Obtener y desencriptar configuración de Comodolar/DolarApp"""
        from utils.security import decrypt_data
        session = self._get_session()
        try:
            query = text("SELECT api_key_enc, api_secret_enc, api_url FROM comodolar_integrations LIMIT 1")
            result = session.execute(query).fetchone()
            if result:
                return {
                    "api_key": decrypt_data(result[0]),
                    "api_secret": decrypt_data(result[1]),
                    "api_url": result[2]
                }
            return None
        finally:
            session.close()

    async def obtener_usuario(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtener un usuario por su nombre de usuario"""
        session = self._get_session()
        try:
            query = text("SELECT username, password_hash, full_name, is_active FROM usuarios WHERE username = :username")
            result = session.execute(query, {"username": username}).fetchone()
            if result:
                return {
                    "username": result[0],
                    "password_hash": result[1],
                    "full_name": result[2],
                    "is_active": result[3]
                }
            return None
        finally:
            session.close()

    async def obtener_estado_transaccion(self, hash_transaccion: str) -> Dict[str, Any]:
        """Obtener el estado de una transacción (implementación básica)"""
        return {"hash": hash_transaccion, "estado": "procesando", "timestamp": datetime.now().isoformat()}
