"""Lógica de evaluación de la matriz de amenazas 3x3.

Aplica las reglas del proyecto de forma simple y directa:
- Sin objetos (todo en 0): sin peligro.
- Un objeto sin vecinos contiguos (aislado): peligro de choque directo contra la nave.
- Dos o más objetos vecinos contiguos (en fila o curva perimetral): paso seguro de lado.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List
import numpy as np

from src.common.constants import PERIMETER_SECTORS, SECTOR_COORDINATES, Sector


class DecisionType(str, Enum):
    """Categorías de decisión de la nave."""

    NO_THREAT = "Sin peligro"          # No hay objetos cerca
    SAFE_TRANSIT = "Paso seguro"        # Los objetos pasan de lado sin chocar
    RED_ALERT = "Peligro de choque"     # Un objeto viene directo hacia la nave


@dataclass
class EvasionDecision:
    """Estructura simple con el resultado de la decisión tomada."""

    decision: DecisionType
    active_sectors: List[Sector]
    consecutive_groups: List[List[Sector]]
    isolated_sectors: List[Sector]
    explanation: str
    action_taken: str


class EvasionEvaluator:
    """Evalúa la cuadrícula 3x3 y decide qué maniobra debe realizar la nave."""

    def __init__(self) -> None:
        """Guarda la lista de los 8 sectores en orden circular horario."""
        # Orden perimetral: [NO, N, NE, E, SE, S, SO, O]
        self.perimeter = PERIMETER_SECTORS

    def evaluate(self, grid: np.ndarray) -> EvasionDecision:
        """Revisa la matriz y clasifica la situación con lógica simple y directa."""
        # 1. Buscar cuáles sectores tienen detección activa (valor igual a 1)
        active_sectors = []
        for sector in self.perimeter:
            fila, columna = SECTOR_COORDINATES[sector]
            if grid[fila, columna] == 1:
                active_sectors.append(sector)

        # Caso 1: Si no hay ningún sector con 1, el espacio está despejado
        if len(active_sectors) == 0:
            return EvasionDecision(
                decision=DecisionType.NO_THREAT,
                active_sectors=[],
                consecutive_groups=[],
                isolated_sectors=[],
                explanation="Espacio libre. No se detecta ningún objeto cerca.",
                action_taken="Seguir la ruta normal sin cambios.",
            )

        # 2. Para cada sector activo, verificar si tiene al menos un vecino contiguo activo
        total_sectores = len(self.perimeter)
        sectores_aislados = []
        sectores_conectados = []

        for i in range(total_sectores):
            sector_actual = self.perimeter[i]

            # Solo evaluamos los sectores que detectaron un objeto
            if sector_actual in active_sectors:
                # El vecino anterior y el siguiente en el círculo perimetral
                vecino_anterior = self.perimeter[(i - 1) % total_sectores]
                vecino_siguiente = self.perimeter[(i + 1) % total_sectores]

                # Si alguno de sus vecinos también tiene detección, van juntos
                if (vecino_anterior in active_sectors) or (vecino_siguiente in active_sectors):
                    sectores_conectados.append(sector_actual)
                else:
                    # Si no tiene ningún vecino activo a los lados, está solitario
                    sectores_aislados.append(sector_actual)

        # Caso 2: Si hay al menos un sector aislado, apunta directo a la nave (alerta)
        if len(sectores_aislados) > 0:
            nombres = ", ".join(s.value for s in sectores_aislados)
            return EvasionDecision(
                decision=DecisionType.RED_ALERT,
                active_sectors=active_sectors,
                consecutive_groups=[sectores_conectados] if sectores_conectados else [],
                isolated_sectors=sectores_aislados,
                explanation=f"Se detectó un objeto solitario en {nombres} que viene directo hacia la nave.",
                action_taken="Mover la nave para esquivarlo y activar escudos.",
            )

        # Caso 3: Dos o más sectores contiguos y ninguno aislado (tránsito seguro de lado)
        if len(sectores_conectados) >= 2 and len(sectores_aislados) == 0:
            nombres = ", ".join(s.value for s in sectores_conectados)
            return EvasionDecision(
                decision=DecisionType.SAFE_TRANSIT,
                active_sectors=active_sectors,
                consecutive_groups=[sectores_conectados],
                isolated_sectors=[],
                explanation=f"Los objetos van pasando de lado por los sectores [{nombres}] sin chocar.",
                action_taken="Mantener el rumbo normal. El paso no representa peligro.",
            )

        # Por precaución si ocurre alguna combinación inesperada
        return EvasionDecision(
            decision=DecisionType.RED_ALERT,
            active_sectors=active_sectors,
            consecutive_groups=[],
            isolated_sectors=active_sectors,
            explanation="Movimiento dudoso alrededor de la nave.",
            action_taken="Mantener escudos listos por precaución.",
        )
