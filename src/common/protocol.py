"""Protocolo de comunicación y estructuras de datos para el paso de mensajes mpi.

Define las clases de mensajes intercambiadas entre los nodos sensores y la nave espacial.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import time

from src.common.constants import Sector


@dataclass
class ThreatEvent:
    """Estructura de datos para enviar una detección de radar a la nave central."""

    # Número incremental del reporte emitido por este sensor
    sequence_id: int

    # Nombre del sector cardinal o intercardinal desde donde se detecta
    sector: Sector

    # Número de proceso mpi del sensor remitente
    rank: int

    # Valor binario: 1 si detectó un meteorito o basura espacial, 0 si está despejado
    detected: int

    # Marca de tiempo en segundos para registrar el momento exacto de la detección
    timestamp: float

    # Texto opcional para indicar la trayectoria estimada del objeto detectado
    trajectory_hint: Optional[str] = None

    # Número del ciclo temporal o paso de la simulación
    step_id: int = 0

    @classmethod
    def create(
        cls,
        sequence_id: int,
        sector: Sector,
        rank: int,
        detected: int,
        step_id: int = 0,
        trajectory_hint: Optional[str] = None,
    ) -> "ThreatEvent":
        """Función auxiliar para instanciar el evento guardando la hora del sistema de forma automática."""
        return cls(
            sequence_id=sequence_id,
            sector=sector,
            rank=rank,
            detected=detected,
            timestamp=time.time(),  # Guarda los segundos actuales con decimales
            trajectory_hint=trajectory_hint,
            step_id=step_id,
        )


@dataclass
class HeartbeatMessage:
    """Mensaje periódico que el sensor manda a la nave para avisar que sigue en funcionamiento."""

    # Sector que tiene asignado el sensor
    sector: Sector

    # Número de proceso mpi del sensor
    rank: int

    # Momento en que se emite el latido
    timestamp: float

    # Bandera para confirmar que el nodo sigue operativo
    is_alive: bool = True

    # Nivel simulado de energía de la batería del sensor (de 0 a 100)
    battery_level: float = 100.0

    @classmethod
    def create(cls, sector: Sector, rank: int, battery_level: float = 100.0) -> "HeartbeatMessage":
        """Función auxiliar para crear un latido con la hora actual."""
        return cls(
            sector=sector,
            rank=rank,
            timestamp=time.time(),
            is_alive=True,
            battery_level=battery_level,
        )


@dataclass
class ReconfigMessage:
    """Mensaje que la nave puede mandar a un sensor para reasignarle sectores en caso de fallas."""

    # Rango mpi del sensor que debe asumir la nueva tarea
    target_rank: int

    # Tupla con los sectores que ahora debe vigilar este sensor
    assigned_sectors: Tuple[Sector, ...]

    # Hora en que se solicitó la reconfiguración
    timestamp: float

    @classmethod
    def create(cls, target_rank: int, assigned_sectors: Tuple[Sector, ...]) -> "ReconfigMessage":
        """Función auxiliar para construir la orden de reconfiguración."""
        return cls(
            target_rank=target_rank,
            assigned_sectors=assigned_sectors,
            timestamp=time.time(),
        )
