"""Servidor central (la nave espacial - rango 0).

Coordina la recolección de detecciones de los 8 sensores, actualiza la matriz de amenazas 3x3,
evalúa colisiones vs tránsitos seguros y supervisa la tolerancia a fallas.
"""

import time
from typing import Optional
from mpi4py import MPI

from src.common.constants import (
    MessageTag,
    SECTOR_TO_RANK,
)
from src.common.protocol import HeartbeatMessage, ReconfigMessage, ThreatEvent
from src.server.evasion_logic import EvasionEvaluator
from src.server.failure_detector import FailureDetector
from src.server.threat_matrix import ThreatMatrix
from src.visualization.console_display import ConsoleDisplay


class ShipServer:
    """Proceso central de mando de la nave espacial (rango 0 en mpi)."""

    def __init__(
        self,
        comm: MPI.Comm,
        heartbeat_timeout: float = 4.0,
        enable_display: bool = True,
    ) -> None:
        """Inicializa las estructuras de datos y subsistemas del centro de mando."""
        self.comm = comm                                                # Canal de comunicación mpi
        self.threat_matrix = ThreatMatrix()                             # Cuadrícula 3x3 de amenazas
        self.evaluator = EvasionEvaluator()                             # Motor de reglas de colisión
        self.failure_detector = FailureDetector(timeout_seconds=heartbeat_timeout)  # Monitor de fallas
        self.display = ConsoleDisplay() if enable_display else None      # Salida gráfica en consola
        self.running = False                                            # Estado del bucle de ejecución
        self.cycle_count = 0                                            # Contador de iteraciones

    def process_incoming_messages(self) -> int:
        """Sondea y vacía la cola de mensajes mpi sin bloquear la ejecución."""
        status = MPI.Status()
        messages_processed = 0

        # Sondeo no bloqueante con Iprobe:
        # Revisa si hay algún mensaje esperando en el buzón proveniente de cualquier sensor (ANY_SOURCE)
        # Esto previene bloqueos mutuos (deadlocks) si los sensores envían a velocidades distintas
        while self.comm.Iprobe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status):
            tag = status.Get_tag()
            source = status.Get_source()

            # Caso A: Mensaje con lectura de radar
            if tag == MessageTag.DETECTION:
                event: ThreatEvent = self.comm.recv(source=source, tag=tag)
                # Actualiza la cuadrícula 3x3 con el 0 o 1 recibido
                self.threat_matrix.apply_event(event)
                messages_processed += 1

            # Caso B: Mensaje con latido periódico del sensor
            elif tag == MessageTag.HEARTBEAT:
                heartbeat: HeartbeatMessage = self.comm.recv(source=source, tag=tag)
                # Registra que el sensor sigue con vida
                released_substitute = self.failure_detector.register_heartbeat(heartbeat)

                # Si el sensor acaba de revivir (estaba caído y retornó a la vida):
                if self.failure_detector.just_recovered:
                    recovered_sec = self.failure_detector.just_recovered
                    self.failure_detector.just_recovered = None

                    # Revisa si algún sector huérfano (que era zona ciega) ahora puede ser cubierto
                    self.failure_detector.reassign_orphaned_sectors()

                    # Envía orden de reconfiguración al nodo recuperado para reconfirmar su área de cobertura
                    rec_rank = SECTOR_TO_RANK[recovered_sec]
                    assigned_rec = tuple(
                        s for s, cov in self.failure_detector.coverage_assignment.items()
                        if cov == recovered_sec
                    )
                    reconfig_rec = ReconfigMessage.create(
                        target_rank=rec_rank,
                        assigned_sectors=assigned_rec,
                    )
                    try:
                        self.comm.send(reconfig_rec, dest=rec_rank, tag=MessageTag.RECONFIG)
                    except Exception:
                        pass

                # Si el sensor revivió, notifica al antiguo sustituto para que libere la zona delegada
                if released_substitute:
                    sub_rank = SECTOR_TO_RANK[released_substitute]
                    assigned = tuple(
                        s for s, cov in self.failure_detector.coverage_assignment.items()
                        if cov == released_substitute
                    )
                    reconfig = ReconfigMessage.create(
                        target_rank=sub_rank,
                        assigned_sectors=assigned,
                    )
                    try:
                        self.comm.send(reconfig, dest=sub_rank, tag=MessageTag.RECONFIG)
                    except Exception:
                        pass
                messages_processed += 1

            # Caso C: Cualquier otro mensaje que pudiera llegar
            else:
                _ = self.comm.recv(source=source, tag=tag)

        return messages_processed

    def run(self, max_cycles: Optional[int] = None, cycle_delay: float = 1.0) -> None:
        """Bucle principal del centro de mando de la nave."""
        self.running = True

        try:
            while self.running:
                self.cycle_count += 1

                # 1. Recibir y procesar todos los mensajes que hayan llegado de los sensores
                self.process_incoming_messages()

                # 2. Revisar si algún sensor dejó de mandar latidos y se considera caído
                failed_sectors = self.failure_detector.check_failures()
                if failed_sectors:
                    # Asigna cobertura a los recién caídos y reasigna sectores huérfanos
                    for failed in failed_sectors:
                        _ = self.failure_detector.get_covering_sensor(failed)
                    self.failure_detector.reassign_orphaned_sectors()

                    # Envía las órdenes de reconfiguración a los sensores activos encargados
                    covered_targets = set()
                    for s, cov in self.failure_detector.coverage_assignment.items():
                        if cov and self.failure_detector.active_status.get(cov, False):
                            covered_targets.add(cov)

                    for cov_sec in covered_targets:
                        covering_rank = SECTOR_TO_RANK[cov_sec]
                        assigned = tuple(
                            s for s, c in self.failure_detector.coverage_assignment.items()
                            if c == cov_sec
                        )
                        reconfig = ReconfigMessage.create(
                            target_rank=covering_rank,
                            assigned_sectors=assigned,
                        )
                        try:
                            self.comm.send(reconfig, dest=covering_rank, tag=MessageTag.RECONFIG)
                        except Exception:
                            pass

                # 3. Limpiar datos estancados en sectores que quedaron como zonas ciegas reales
                for sector, covering in self.failure_detector.coverage_assignment.items():
                    if covering is None:
                        self.threat_matrix.update_sector(sector, 0)

                # 4. Leer el estado actual de la matriz 3x3 y evaluar si hay colisión o tránsito seguro
                current_grid = self.threat_matrix.grid
                decision = self.evaluator.evaluate(current_grid)

                # 5. Mostrar en pantalla el tablero visual con colores
                if self.display:
                    self.display.render_dashboard(
                        grid=current_grid,
                        decision=decision,
                        sensor_status=self.failure_detector.active_status,
                        cycle_number=self.cycle_count,
                        coverage_assignment=self.failure_detector.coverage_assignment,
                        recently_recovered=list(self.failure_detector.recently_recovered),
                    )
                    # Limpia la lista de reactivaciones para que no se repitan en ciclos futuros
                    self.failure_detector.recently_recovered.clear()

                # Si se alcanzó el número máximo de ciclos solicitado, salimos del bucle
                if max_cycles is not None and self.cycle_count >= max_cycles:
                    break

                # Pausa antes del siguiente ciclo de monitoreo
                time.sleep(cycle_delay)

        finally:
            # Al terminar o ser interrumpido, apaga ordenadamente a todos los sensores
            self.shutdown()

    def shutdown(self) -> None:
        """Envía un mensaje de parada a los 8 sensores para cerrar la simulación limpiamente."""
        self.running = False
        for sector, rank in SECTOR_TO_RANK.items():
            try:
                # Manda la etiqueta TERMINATE para que el sensor salga de su bucle
                self.comm.send(None, dest=rank, tag=MessageTag.TERMINATE)
            except Exception:
                pass
