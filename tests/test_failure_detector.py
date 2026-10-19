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
    detector = FailureDetector(timeout_seconds=0.1, startup_grace_period=0.0)

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
    detector = FailureDetector(timeout_seconds=1.0, startup_grace_period=0.0)

    # Supongamos que el sensor Sur (S) cae
    detector.active_status[Sector.S] = False

    # El vecino de la derecha en sentido horario desde S es SO
    covering = detector.get_covering_sensor(Sector.S)
    assert covering == Sector.SO
    assert detector.coverage_assignment[Sector.S] == Sector.SO


def test_heartbeat_keeps_sensor_alive() -> None:
    """Verifica que recibir un latido mantenga al sensor activo y reinicie su temporizador."""
    detector = FailureDetector(timeout_seconds=0.2, startup_grace_period=0.0)

    # Simulamos una pequeña espera pero enviamos latido de Sector.N antes del timeout
    time.sleep(0.1)
    msg = HeartbeatMessage.create(sector=Sector.N, rank=2)
    detector.register_heartbeat(msg)

    # Esperamos otro poco de tiempo donde los demás vencen pero N sigue vigente
    time.sleep(0.12)
    failed = detector.check_failures()

    assert Sector.N not in failed
    assert detector.active_status[Sector.N] is True


def test_adjacent_neighbor_failure_cascade() -> None:
    """Verifica qué ocurre si primero cae un sensor y luego también cae su vecino sustituto."""
    detector = FailureDetector(timeout_seconds=1.0)

    # 1. Cae el sensor Sur (S) -> se asigna a su vecino SO
    detector.active_status[Sector.S] = False
    covering_1 = detector.get_covering_sensor(Sector.S)
    assert covering_1 == Sector.SO

    # 2. Ahora también cae el vecino SO (que estaba cubriendo a S)
    detector.active_status[Sector.SO] = False

    # Al reasignar los huérfanos:
    # - S busca a su siguiente vecino activo (su otro vecino directo SE)
    # - SO se reasigna a su vecino directo O
    reassigned = detector.reassign_orphaned_sectors()
    detector.get_covering_sensor(Sector.SO)

    assert detector.coverage_assignment[Sector.S] == Sector.SE
    assert detector.coverage_assignment[Sector.SO] == Sector.O


def test_both_immediate_neighbors_failure() -> None:
    """Verifica que si caen ambos vecinos directos (+1 y -1), se declare zona ciega sin cobertura."""
    detector = FailureDetector(timeout_seconds=1.0)

    # Caen S y sus dos vecinos directos (SO y SE)
    detector.active_status[Sector.S] = False
    detector.active_status[Sector.SO] = False
    detector.active_status[Sector.SE] = False

    # El detector no inventa visión a través de la nave; declara zona ciega
    covering = detector.get_covering_sensor(Sector.S)
    assert covering is None
    assert detector.coverage_assignment[Sector.S] is None


def test_recovered_sensor_restores_assignment() -> None:
    """Verifica que si un sensor caído vuelve a enviar latidos, recupere su zona y libere al sustituto."""
    detector = FailureDetector(timeout_seconds=1.0, startup_grace_period=0.0)

    # 1. El sensor S cae y se asigna al sustituto SO
    detector.active_status[Sector.S] = False
    _ = detector.get_covering_sensor(Sector.S)
    assert detector.coverage_assignment[Sector.S] == Sector.SO

    # 2. El sensor S revive y envía un nuevo latido
    msg = HeartbeatMessage.create(sector=Sector.S, rank=7)
    released_substitute = detector.register_heartbeat(msg)

    # Debe identificar a SO como el sustituto que debe ser liberado
    assert released_substitute == Sector.SO
    # S vuelve a vigilarse a sí mismo
    assert detector.coverage_assignment[Sector.S] == Sector.S
    assert detector.active_status[Sector.S] is True

