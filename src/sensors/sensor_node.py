"""Implementación del nodo sensor periférico (escáner de sector).

Cada sensor ejecuta un bucle de escaneo de su sector espacial, detecta posibles objetos
(meteoritos o basura espacial) y reporta las alertas al servidor central mediante mpi.
"""

import time
from typing import Optional
from mpi4py import MPI

from src.common.constants import MessageTag, SERVER_RANK, Sector
from src.common.prng import SharedSeedPRNG
from src.common.protocol import HeartbeatMessage, ReconfigMessage, ThreatEvent


class SensorNode:
    """Representa a uno de los 8 radares periféricos colocados alrededor de la nave."""

    def __init__(
        self,
        comm: MPI.Comm,
        rank: int,
        sector: Sector,
        seed: int = 42,
        scan_interval: float = 0.8,
        heartbeat_interval: float = 2.0,
        fail_at_cycle: Optional[int] = None,
    ) -> None:
        """Configura los parámetros iniciales de conexión y escaneo del sensor."""
        self.comm = comm                          # Canal de comunicación mpi
        self.rank = rank                          # Número de proceso de este sensor (del 1 al 8)
        self.sector = sector                      # Nombre del sector asignado (ejemplo: N, SO, etc.)
        self.scan_interval = scan_interval        # Segundos de espera entre cada lectura de radar
        self.heartbeat_interval = heartbeat_interval  # Segundos de espera entre cada latido de vida
        self.fail_at_cycle = fail_at_cycle        # Ciclo a partir del cual el sensor simulará su caída

        # Crea el generador determinista personalizando la semilla con el rango del nodo
        # De este modo cada sensor tiene su propia secuencia única y reproducible
        self.prng = SharedSeedPRNG(seed=seed + rank * 100)

        self.sequence_id = 0                      # Contador de mensajes emitidos
        self.step_id = 0                          # Contador de pasos temporales
        self.running = False                      # Bandera para saber si el bucle sigue activo
        self.covered_sectors = [sector]           # Lista de sectores que vigila actualmente

    def send_heartbeat(self) -> None:
        """Empaqueta y envía un latido hacia la nave (rango 0) para indicar que sigue activo."""
        heartbeat = HeartbeatMessage.create(sector=self.sector, rank=self.rank)
        # Envía el objeto por mpi con la etiqueta de latido
        self.comm.send(heartbeat, dest=SERVER_RANK, tag=MessageTag.HEARTBEAT)

    def scan_environment(self, sector: Optional[Sector] = None) -> ThreatEvent:
        """Simula una lectura de radar para saber si hay o no un objeto en el sector."""
        target_sector = sector if sector is not None else self.sector
        self.sequence_id += 1
        self.step_id += 1

        # Genera un número decimal entre 0.0 y 1.0 usando el prng determinista
        chance = self.prng.next_float()

        # Si el valor supera 0.65 se considera detección positiva (1), de lo contrario 0
        if chance > 0.65:
            detected = 1
            if self.prng.next_float() > 0.5:
                hint = "colisión directa"
            else:
                hint = "tránsito perimetral"
        else:
            detected = 0
            hint = "despejado"

        # Construye el evento con la información del radar
        return ThreatEvent.create(
            sequence_id=self.sequence_id,
            sector=target_sector,
            rank=self.rank,
            detected=detected,
            step_id=self.step_id,
            trajectory_hint=hint,
        )

    def run(self, max_cycles: Optional[int] = None) -> None:
        """Bucle principal de trabajo del nodo sensor."""
        self.running = True
        last_heartbeat = 0.0
        cycles = 0

        while self.running:
            # 1. Revisa de forma no bloqueante si la nave envió una orden de apagado general
            if self.comm.Iprobe(source=SERVER_RANK, tag=MessageTag.TERMINATE):
                _ = self.comm.recv(source=SERVER_RANK, tag=MessageTag.TERMINATE)
                self.running = False
                break

            # 2. Si este sensor está programado para fallar y alcanzó el ciclo indicado
            if self.fail_at_cycle is not None and cycles >= self.fail_at_cycle:
                # El sensor simula una falla guardando silencio: no emite latidos ni lecturas.
                # Permanece en espera no bloqueante hasta que la nave ordene la terminación.
                time.sleep(0.3)
                continue

            # 3. Revisa si la nave le asignó sectores adicionales por tolerancia a fallas
            if self.comm.Iprobe(source=SERVER_RANK, tag=MessageTag.RECONFIGURE):
                reconfig_msg: ReconfigMessage = self.comm.recv(
                    source=SERVER_RANK, tag=MessageTag.RECONFIGURE
                )
                self.covered_sectors = list(reconfig_msg.assigned_sectors)

            now = time.time()

            # 4. Si ya pasó el tiempo estipulado, envía un latido a la nave
            if now - last_heartbeat >= self.heartbeat_interval:
                self.send_heartbeat()
                last_heartbeat = now

            # 5. Realiza la lectura del radar para cada sector bajo su vigilancia y envía los datos
            for sec in self.covered_sectors:
                event = self.scan_environment(sector=sec)
                self.comm.send(event, dest=SERVER_RANK, tag=MessageTag.DETECTION)

            cycles += 1
            # 6. Si se configuró un número límite de ciclos y ya se alcanzó, finaliza el sensor
            if max_cycles is not None and cycles >= max_cycles:
                break

            # Pausa breve antes de realizar el siguiente escaneo
            time.sleep(self.scan_interval)
