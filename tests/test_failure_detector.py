"""Pruebas unitarias para el detector de fallas y reasignación de sectores vecinos.

¿Cómo funciona pytest en este archivo?
-------------------------------------
pytest ejecuta automáticamente estas pruebas para validar que el monitor de latidos
detecte cuando un sensor deja de responder y reasigne dinámicamente la cobertura
al vecino correspondiente en el anillo perimetral.
"""

import time
from src.common.constants import Sector
from src.common.protocol import HeartbeatMessage
from src.server.failure_detector import FailureDetector


def test_failure_detection_timeout() -> None:
    """Verifica que el detector identifique a un sensor que supera el tiempo límite."""
    detector = FailureDetector(timeout_seconds=0.1)

    # Inicialmente todos están activos
    for sector in Sector:
        assert detector.active_status[sector] is True

    # Simulamos que pasa el tiempo límite
    time.sleep(0.15)

    # check_failures debe retornar todos los sectores caídos
    failed = detector.check_failures()
    assert len(failed) == 8
    for sector in Sector:
        assert detector.active_status[sector] is False


def test_neighbor_reallocation_on_failure() -> None:
    """Verifica que un sensor caído sea reasignado a su vecino inmediato."""
    detector = FailureDetector(timeout_seconds=1.0)

    # Supongamos que el sensor Sur (S) cae
    detector.active_status[Sector.S] = False

    # El vecino de la derecha en sentido horario desde S es SO
    covering = detector.get_covering_sensor(Sector.S)
    assert covering == Sector.SO
    assert detector.coverage_assignment[Sector.S] == Sector.SO


def test_heartbeat_keeps_sensor_alive() -> None:
    """Verifica que recibir un latido mantenga al sensor activo y reinicie su temporizador."""
    detector = FailureDetector(timeout_seconds=0.2)

    # Simulamos una pequeña espera pero enviamos latido de Sector.N antes del timeout
    time.sleep(0.1)
    msg = HeartbeatMessage.create(sector=Sector.N, rank=2)
    detector.register_heartbeat(msg)

    # Esperamos otro poco de tiempo donde los demás vencen pero N sigue vigente
    time.sleep(0.12)
    failed = detector.check_failures()

    assert Sector.N not in failed
    assert detector.active_status[Sector.N] is True
