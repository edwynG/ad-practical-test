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

    def __init__(self, timeout_seconds: float = 3.0, startup_grace_period: float = 2.0) -> None:
        """Configura el tiempo máximo de espera antes de declarar caído un sensor."""
        self.timeout_seconds = timeout_seconds
        self.startup_grace_period = startup_grace_period
        self.start_time = time.time()

        # Guarda la hora del último latido recibido de cada sector (inicia con la hora actual)
        self.last_heartbeat: Dict[Sector, float] = {s: time.time() for s in Sector}

        # Estado operativo actual de cada sector (True si está vivo, False si cayó)
        self.active_status: Dict[Sector, bool] = {s: True for s in Sector}

        # Registro de qué sensor se encarga de vigilar cada sector (puede ser None si no hay sustituto)
        self.coverage_assignment: Dict[Sector, Optional[Sector]] = {s: s for s in Sector}

    def register_heartbeat(self, message: HeartbeatMessage) -> Optional[Sector]:
        """Actualiza el reloj cada vez que llega un latido nuevo de un sensor.

        Si el sensor estaba marcado como caído y vuelve a responder, restaura su asignación
        original y retorna el sector del antiguo sustituto para que libere la zona delegada.
        """
        now = time.time()
        self.last_heartbeat[message.sector] = now

        was_dead = not self.active_status.get(message.sector, True)
        self.active_status[message.sector] = True

        old_covering = self.coverage_assignment.get(message.sector)
        if was_dead:
            # El sensor recuperado retoma el control exclusivo de su propia zona
            self.coverage_assignment[message.sector] = message.sector
            if old_covering and old_covering != message.sector:
                return old_covering
        return None

    def check_failures(self) -> List[Sector]:
        """Revisa la lista de sensores y detecta si alguno superó el tiempo límite sin responder."""
        now = time.time()
        # Período de gracia inicial al arrancar para evitar falsas alarmas mientras inician los procesos
        if now - self.start_time < self.startup_grace_period:
            return []

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
        """Busca el sensor vecino inmediato activo (derecha o izquierda) para cubrir a un sensor caído."""
        # Si el sensor original sigue activo, se vigila a sí mismo
        if self.active_status[sector]:
            self.coverage_assignment[sector] = sector
            return sector

        # Posición del sector en el anillo perimetral de 8 sectores
        posicion = PERIMETER_SECTORS.index(sector)
        total = len(PERIMETER_SECTORS)

        # 1. Probar primero con el vecino de la derecha (+1 en sentido horario)
        vecino_derecho = PERIMETER_SECTORS[(posicion + 1) % total]
        if self.active_status[vecino_derecho]:
            self.coverage_assignment[sector] = vecino_derecho
            return vecino_derecho

        # 2. Si el de la derecha está caído, probar con el vecino de la izquierda (-1 en sentido antihorario)
        vecino_izquierdo = PERIMETER_SECTORS[(posicion - 1) % total]
        if self.active_status[vecino_izquierdo]:
            self.coverage_assignment[sector] = vecino_izquierdo
            return vecino_izquierdo

        # Si ninguno de sus dos vecinos directos está disponible, es una zona ciega real
        self.coverage_assignment[sector] = None
        return None

    def reassign_orphaned_sectors(self) -> Dict[Sector, Optional[Sector]]:
        """Revisa y reasigna los sectores caídos cuyo sensor sustituto también haya fallado."""
        reassigned = {}
        for sector, active in self.active_status.items():
            if not active:
                current_covering = self.coverage_assignment.get(sector)
                # Si no tiene sustituto o el que tenía asignado acaba de caer
                if current_covering is None or not self.active_status.get(current_covering, False):
                    new_covering = self.get_covering_sensor(sector)
                    reassigned[sector] = new_covering
        return reassigned
