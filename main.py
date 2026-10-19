"""Punto de entrada principal del sistema distribuido Aegis-Star.

Ejecuta el servidor central (nave) en el rango 0 y los 8 nodos sensores en los rangos 1 al 8.
"""

import argparse
import sys
from mpi4py import MPI

from src.common.constants import (
    RANK_TO_SECTOR,
    SERVER_RANK,
    TOTAL_PROCESSES,
)
from src.sensors.sensor_node import SensorNode
from src.server.ship_server import ShipServer


def parse_arguments() -> argparse.Namespace:
    """Lee y procesa los parámetros que el usuario escribe en la terminal."""
    parser = argparse.ArgumentParser(
        description="Sistema de detección y evasión en estrella (Aegis-Star 8-Sector)"
    )
    # Permite fijar cuántos ciclos durará la simulación (por defecto 8)
    parser.add_argument(
        "--cycles",
        type=int,
        default=8,
        help="Cantidad de ciclos a ejecutar antes de finalizar (por defecto 8, 0 para indefinido)",
    )
    # Permite ajustar el tiempo de espera entre ciclos en segundos
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Demora en segundos entre ciclos de evaluación (por defecto 1.0)",
    )
    # Permite fijar una semilla para que los números pseudoaleatorios sean repetibles
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla compartida para el generador pseudoaleatorio determinista",
    )
    # Permite simular la caída de un sensor para probar tolerancia a fallas
    parser.add_argument(
        "--fail-sensor",
        type=lambda s: s.strip().upper(),
        default=None,
        choices=["NO", "N", "NE", "O", "E", "SO", "S", "SE"],
        help="Sector del sensor que fallará para simular tolerancia a fallas (ejemplo: S, N, O)",
    )
    # Permite indicar en qué ciclo debe fallar el sensor indicado
    parser.add_argument(
        "--fail-at",
        type=int,
        default=3,
        help="Número de ciclo en el que ocurrirá la desconexión del sensor indicado (por defecto 3)",
    )
    return parser.parse_args()


def main() -> None:
    """Función de inicio que revisa qué rol debe cumplir cada proceso según su rango mpi."""
    # Inicializa el comunicador global de mpi
    comm = MPI.COMM_WORLD

    # Obtiene el número identificador único de este proceso (del 0 al 8)
    rank = comm.Get_rank()

    # Obtiene cuántos procesos se lanzaron en total con mpirun
    size = comm.Get_size()

    # Lee las opciones pasadas por línea de comandos
    args = parse_arguments()

    # Verificación de seguridad: el sistema requiere exactamente 9 procesos (1 nave + 8 sensores)
    if size != TOTAL_PROCESSES:
        # Solo el proceso 0 imprime el mensaje de error para evitar que salgan mensajes repetidos
        if rank == 0:
            print(
                f"Error: se requieren exactamente {TOTAL_PROCESSES} procesos mpi (1 servidor central + 8 sensores). "
                f"Procesos actuales: {size}.\n"
                f"Ejecución recomendada: mpirun -n 9 --oversubscribe .venv/bin/python main.py",
                file=sys.stderr,
            )
        sys.exit(1)

    # Si se especificó un número mayor a cero, se usa como límite de ciclos
    max_cycles = args.cycles if args.cycles > 0 else None

    # Rol 1: Si el proceso tiene rango 0, asume el papel de la nave espacial (servidor central)
    if rank == SERVER_RANK:
        timeout = max(1.5, args.delay * 1.5)
        server = ShipServer(comm=comm, heartbeat_timeout=timeout, enable_display=True)
        try:
            # Ejecuta el bucle del centro de mando
            server.run(max_cycles=max_cycles, cycle_delay=args.delay)
        except KeyboardInterrupt:
            # Si el usuario presiona Ctrl+C en la consola, apaga ordenadamente
            server.shutdown()

    # Rol 2: Si el proceso tiene rango del 1 al 8, asume el papel del sensor asignado a ese rango
    elif rank in RANK_TO_SECTOR:
        # Averigua qué sector cardinal o intercardinal le corresponde
        sector = RANK_TO_SECTOR[rank]

        # Determina si a este sensor en particular le corresponde simular una falla
        fail_at_cycle = (
            args.fail_at
            if args.fail_sensor and args.fail_sensor == sector.value
            else None
        )

        scan_int = max(0.4, args.delay * 0.7)
        hb_int = max(0.5, args.delay * 0.7)

        # Crea la instancia del sensor con sus parámetros
        sensor = SensorNode(
            comm=comm,
            rank=rank,
            sector=sector,
            seed=args.seed,
            scan_interval=scan_int,
            heartbeat_interval=hb_int,
            fail_at_cycle=fail_at_cycle,
        )
        try:
            # Inicia el bucle de escaneo del sensor
            sensor.run(max_cycles=max_cycles * 3 if max_cycles else None)
        except KeyboardInterrupt:
            pass

    # Si hubiera algún proceso sobrante con rango superior a 8, simplemente no hace nada
    else:
        pass


if __name__ == "__main__":
    main()
