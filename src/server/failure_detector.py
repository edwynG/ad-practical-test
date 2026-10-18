"""Detector de fallas y monitor de latidos (heartbeats).

Monitorea la actividad de los 8 nodos sensores, detecta desconexiones por temporizador
y calcula la reconfiguración dinámica de cobertura de radar para los sectores ciegos.
"""

from typing import Dict, List, Optional
import time

from src.common.constants import PERIMETER_SECTORS, Sector
from src.common.protocol import HeartbeatMessage


class FailureDetector:
    """Supervisa que todos los nodos periféricos sigan respondiendo a tiempo."""

    def __init__(self, timeout_seconds: float = 3.0) -> None:
        """Configura el tiempo máximo de espera antes de declarar caído un sensor."""
        # Si un sensor no manda latidos durante más de timeout_seconds, se asume desconectado
        self.timeout_seconds = timeout_seconds

        # Guarda la hora del último latido recibido de cada sector (inicia con la hora actual)
        self.last_heartbeat: Dict[Sector, float] = {s: time.time() for s in Sector}

        # Estado operativo actual de cada sector (True si está vivo, False si cayó)
        self.active_status: Dict[Sector, bool] = {s: True for s in Sector}

        # Registro de qué sensor se encarga de vigilar cada sector
        self.coverage_assignment: Dict[Sector, Sector] = {s: s for s in Sector}

    def register_heartbeat(self, message: HeartbeatMessage) -> None:
        """Actualiza el reloj cada vez que llega un latido nuevo de un sensor."""
        # Actualiza la hora del último latido a la hora actual
        self.last_heartbeat[message.sector] = time.time()
        # Marca el sector como activo y funcional
        self.active_status[message.sector] = True

    def check_failures(self) -> List[Sector]:
        """Revisa la lista de sensores y detecta si alguno superó el tiempo límite sin responder."""
        now = time.time()
        failed_sectors = []

        # Recorre los 8 sectores y calcula cuánto tiempo ha pasado desde el último latido
        for sector, last_seen in self.last_heartbeat.items():
            if now - last_seen > self.timeout_seconds:
                # Si estaba marcado como activo pero ya se venció el tiempo, lo declara caído
                if self.active_status[sector]:
                    self.active_status[sector] = False
                    failed_sectors.append(sector)

        return failed_sectors

    def get_covering_sensor(self, sector: Sector) -> Optional[Sector]:
        """Busca el sensor vecino activo más cercano para cubrir el punto ciego del sensor caído."""
        # Si el sensor original sigue vivo, no hace falta que nadie lo cubra
        if self.active_status[sector]:
            return sector

        # Encuentra la posición del sensor en el círculo de 8 sectores
        idx = PERIMETER_SECTORS.index(sector)
        perimeter_len = len(PERIMETER_SECTORS)

        # Prueba primero con el vecino inmediato a la derecha (+1) o a la izquierda (-1)
        for offset in [1, -1, 2, -2]:
            candidate = PERIMETER_SECTORS[(idx + offset) % perimeter_len]
            # Si el vecino candidato está funcionando, se le asigna la cobertura
            if self.active_status[candidate]:
                self.coverage_assignment[sector] = candidate
                return candidate

        # Si todos los vecinos estuvieran caídos, no hay nadie para cubrirlo
        return None
