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
                self.failure_detector.register_heartbeat(heartbeat)
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
                for failed in failed_sectors:
                    # Busca qué sensor vecino activo puede asumir la vigilancia de ese sector
                    covering = self.failure_detector.get_covering_sensor(failed)
                    if covering:
                        covering_rank = SECTOR_TO_RANK[covering]
                        # Obtiene todos los sectores asignados ahora a este sensor vecino
                        assigned = tuple(
                            s for s, cov in self.failure_detector.coverage_assignment.items()
                            if cov == covering
                        )
                        reconfig = ReconfigMessage.create(
                            target_rank=covering_rank,
                            assigned_sectors=assigned,
                        )
                        try:
                            self.comm.send(reconfig, dest=covering_rank, tag=MessageTag.RECONFIGURE)
                        except Exception:
                            pass

                # 3. Leer el estado actual de la matriz 3x3 y evaluar si hay colisión o tránsito seguro
                current_grid = self.threat_matrix.grid
                decision = self.evaluator.evaluate(current_grid)

                # 4. Mostrar en pantalla el tablero visual con colores
                if self.display:
                    self.display.render_dashboard(
                        grid=current_grid,
                        decision=decision,
                        sensor_status=self.failure_detector.active_status,
                        cycle_number=self.cycle_count,
                        coverage_assignment=self.failure_detector.coverage_assignment,
                    )

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
