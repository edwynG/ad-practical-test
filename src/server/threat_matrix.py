"""Estructura y gestión de la matriz de amenazas 3x3.

Mantiene el estado espacial de detecciones activas alrededor de la nave central,
permitiendo actualizaciones seguras sin condiciones de carrera.
"""

from typing import List
import numpy as np

from src.common.constants import (
    SECTOR_COORDINATES,
    Sector,
)
from src.common.protocol import ThreatEvent


class ThreatMatrix:
    """Representa la cuadrícula espacial de 3x3 con la nave en el centro."""

    def __init__(self) -> None:
        """Crea una matriz de ceros de 3 filas por 3 columnas usando numpy."""
        # Cada celda almacena 0 (sin amenaza) o 1 (objeto detectado)
        self._grid = np.zeros((3, 3), dtype=int)

    @property
    def grid(self) -> np.ndarray:
        """Devuelve una copia de la matriz para evitar que sea modificada directamente desde fuera."""
        return self._grid.copy()

    def reset(self) -> None:
        """Vuelve a poner todos los valores de la matriz en 0."""
        self._grid.fill(0)

    def update_sector(self, sector: Sector, value: int) -> None:
        """Cambia el valor de una celda específica en la matriz según el sector."""
        # Busca la fila y columna que le corresponde a ese sector (por ejemplo NO es 0, 0)
        row, col = SECTOR_COORDINATES[sector]
        # Si el valor recibido es diferente de cero lo fija en 1, de lo contrario en 0
        self._grid[row, col] = 1 if value else 0

    def apply_event(self, event: ThreatEvent) -> None:
        """Toma el reporte que llegó por mpi y actualiza la cuadrícula."""
        self.update_sector(event.sector, event.detected)

    def get_sector_value(self, sector: Sector) -> int:
        """Permite consultar si un sector específico tiene un 0 o un 1."""
        row, col = SECTOR_COORDINATES[sector]
        return int(self._grid[row, col])

    def count_active_detections(self) -> int:
        """Cuenta cuántos sectores tienen una detección activa (valor 1)."""
        contador = 0
        for fila, columna in SECTOR_COORDINATES.values():
            if self._grid[fila, columna] == 1:
                contador += 1
        return contador

    def active_sectors(self) -> List[Sector]:
        """Devuelve una lista con los nombres de los sectores que tienen detección activa."""
        active = []
        for sector, (row, col) in SECTOR_COORDINATES.items():
            if self._grid[row, col] == 1:
                active.append(sector)
        return active

    def to_formatted_rows(self) -> List[str]:
        """Crea un texto con el formato que pide el documento para imprimir en pantalla."""
        # Nombres de las etiquetas por fila
        labels = [
            ["NO", "N", "NE"],
            ["O", "x", "E"],
            ["SO", "S", "SE"],
        ]
        rows = []
        for r in range(3):
            # Imprime la fila de etiquetas, por ejemplo: [ NO  N NE ]
            label_row = f"[ {labels[r][0]:>2} {labels[r][1]:>2} {labels[r][2]:>2} ]"
            # Si es el centro mostramos una 'x' para representar a la nave
            val_0 = "x" if r == 1 else str(self._grid[r, 0])
            val_1 = "x" if r == 1 else str(self._grid[r, 1])
            val_2 = "x" if r == 1 else str(self._grid[r, 2])
            val_row = f"[ {val_0} {val_1} {val_2} ]"
            # Une las dos partes en una sola línea
            rows.append(f"{label_row}   {val_row}")
        return rows
