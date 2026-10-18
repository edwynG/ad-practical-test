"""Pruebas unitarias para el protocolo de mensajes e instancias de eventos.

¿Cómo funciona pytest en este archivo?
-------------------------------------
pytest importa este módulo e identifica automáticamente las funciones 'test_threat_event_creation'
y 'test_heartbeat_creation'. Al ejecutarlas, valida que las estructuras de datos mantengan
los tipos correctos, calculen automáticamente las marcas de tiempo actuales y permitan
que los mensajes viajen sin pérdida de información a través de mpi.
"""

from src.common.constants import Sector
from src.common.protocol import HeartbeatMessage, ThreatEvent


def test_threat_event_creation() -> None:
    """Verifica que un evento de detección de amenaza se inicialice con todos sus campos correctos."""
    # Creamos un evento simulando que el sensor Norte (rango 2) detectó un objeto
    event = ThreatEvent.create(
        sequence_id=1,
        sector=Sector.N,
        rank=2,
        detected=1,
        step_id=1,
        trajectory_hint="colisión directa",
    )

    # Validamos que los datos dentro del objeto coincidan con lo asignado
    assert event.sector == Sector.N
    assert event.detected == 1
    assert event.rank == 2
    # El timestamp debe ser un número positivo generado automáticamente con la hora actual
    assert event.timestamp > 0
    assert event.trajectory_hint == "colisión directa"


def test_heartbeat_creation() -> None:
    """Verifica que un latido periódico de vida se construya correctamente."""
    # Creamos un latido simulando que el sensor Suroeste reporta 95.5% de batería
    heartbeat = HeartbeatMessage.create(sector=Sector.SO, rank=6, battery_level=95.5)

    # Validamos los campos del mensaje de latido
    assert heartbeat.sector == Sector.SO
    assert heartbeat.rank == 6
    assert heartbeat.is_alive is True
    assert heartbeat.battery_level == 95.5
    assert heartbeat.timestamp > 0
