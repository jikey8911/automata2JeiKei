from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class IAutomatizadorUI(ABC):
    """Puerto para automatización de interfaz de usuario en dispositivos móviles"""
    
    @abstractmethod
    async def conectar(self) -> bool:
        """Conectar al dispositivo/emulador"""
        pass
    
    @abstractmethod
    async def desconectar(self) -> bool:
        """Desconectar del dispositivo"""
        pass
    
    @abstractmethod
    async def tocar_elemento(self, elemento_id: str) -> bool:
        """Tocar un elemento en la pantalla"""
        pass
    
    @abstractmethod
    async def escribir_texto(self, elemento_id: str, texto: str) -> bool:
        """Escribir texto en un campo"""
        pass
    
    @abstractmethod
    async def instalar_app(self, url_apk: str) -> bool:
        """Instalar una aplicación desde URL"""
        pass
    
    @abstractmethod
    async def desinstalar_app(self, nombre_paquete: str) -> bool:
        """Desinstalar una aplicación"""
        pass
    
    @abstractmethod
    async def obtener_captura_pantalla(self) -> Optional[bytes]:
        """Obtener captura de pantalla actual"""
        pass
    
    @abstractmethod
    async def ejecutar_script_personalizado(self, script: str) -> Dict[str, Any]:
        """Ejecutar un script personalizado"""
        pass
    
    @abstractmethod
    async def encontrar_elemento(self, selector: str) -> Optional[str]:
        """Encontrar un elemento por selector"""
        pass
    
    @abstractmethod
    async def esperar_elemento(self, selector: str, timeout: int = 10) -> bool:
        """Esperar a que un elemento aparezca"""
        pass
    
    @abstractmethod
    async def obtener_texto_elemento(self, elemento_id: str) -> Optional[str]:
        """Obtener texto de un elemento"""
        pass
    
    @abstractmethod
    async def limpiar_campo(self, elemento_id: str) -> bool:
        """Limpiar contenido de un campo"""
        pass
    
    @abstractmethod
    async def deslizar_pantalla(self, inicio_x: int, inicio_y: int, fin_x: int, fin_y: int) -> bool:
        """Deslizar en la pantalla"""
        pass
    
    @abstractmethod
    async def presionar_tecla(self, tecla: str) -> bool:
        """Presionar una tecla del dispositivo"""
        pass
