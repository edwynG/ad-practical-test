"""Definición de constantes globales, sectores y etiquetas de comunicación mpi.

Este módulo centraliza las coordenadas de la rejilla 3x3, los rangos asignados a cada nodo
en la topología en estrella y las etiquetas numéricas para los mensajes mpi.
"""

from enum import Enum, IntEnum
from typing import Dict, Tuple

# Rango mpi que identifica al servidor central (la nave espacial)
# En mpi, los procesos se numeran empezando desde 0
SERVER_RANK = 0

# Cantidad de radares periféricos que rodean a la nave espacial
TOTAL_SENSORS = 8

# Total de procesos requeridos en la simulación (1 nave central + 8 sensores periféricos)
TOTAL_PROCESSES = 9


class Sector(str, Enum):
    """Nombres de los 8 sectores cardinales e intercardinales."""

    NO = "NO"  # Noroeste
    N = "N"    # Norte
    NE = "NE"  # Noreste
    O = "O"    # Oeste
    E = "E"    # Este
    SO = "SO"  # Suroeste
    S = "S"    # Sur
    SE = "SE"  # Sureste


# Asigna a cada sector geográfico un número de proceso mpi único del 1 al 8
# El rango 0 queda reservado para la nave central
SECTOR_TO_RANK: Dict[Sector, int] = {
    Sector.NO: 1,
    Sector.N: 2,
    Sector.NE: 3,
    Sector.O: 4,
    Sector.E: 5,
    Sector.SO: 6,
    Sector.S: 7,
    Sector.SE: 8,
}

# Diccionario inverso para saber qué sector le corresponde a un número de proceso mpi
RANK_TO_SECTOR: Dict[int, Sector] = {rank: sector for sector, rank in SECTOR_TO_RANK.items()}

# Ubicación en coordenadas (fila, columna) dentro de la matriz de amenazas 3x3
# La fila 0 es la superior (NO, N, NE)
# La fila 1 es la del medio (O, Nave, E)
# La fila 2 es la inferior (SO, S, SE)
SECTOR_COORDINATES: Dict[Sector, Tuple[int, int]] = {
    Sector.NO: (0, 0),
    Sector.N: (0, 1),
    Sector.NE: (0, 2),
    Sector.O: (1, 0),
    Sector.E: (1, 2),
    Sector.SO: (2, 0),
    Sector.S: (2, 1),
    Sector.SE: (2, 2),
}

# La nave espacial siempre se ubica en el centro de la cuadrícula 3x3
SHIP_COORDINATES: Tuple[int, int] = (1, 1)

# Lista ordenada de los sectores en sentido horario formando un anillo exterior
# Esta lista permite comprobar si dos sensores activados son vecinos inmediatos
PERIMETER_SECTORS = [
    Sector.NO,
    Sector.N,
    Sector.NE,
    Sector.E,
    Sector.SE,
    Sector.S,
    Sector.SO,
    Sector.O,
]


class MessageTag(IntEnum):
    """Etiquetas numéricas para distinguir el propósito de cada mensaje mpi."""

    DETECTION = 100    # Indica que el mensaje contiene una lectura de radar (objeto detectado o no)
    HEARTBEAT = 200    # Indica que el mensaje es un latido periódico para avisar que el sensor está vivo
    RECONFIG = 300     # Indica que la nave solicita a un sensor cubrir el sector de un vecino caído
    RECONFIGURE = 300  # Alias de RECONFIG para compatibilidad semántica
    TERMINATE = 999    # Orden de apagado enviada por la nave a los sensores al finalizar la simulación
