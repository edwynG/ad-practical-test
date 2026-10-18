"""Lógica de clasificación de amenazas y toma de decisiones de evasión.

Aplica las reglas descritas en la especificación:
- Un único 1 aislado: alerta roja por colisión inminente (trayectoria convergente al centro).
- Dos o más 1 consecutivos y adyacentes: tránsito seguro (trayectoria paralela o tangente).
- Sin detecciones: seguro / sin amenazas.
- Casos límite de bordes y ráfagas evaluados mediante el ciclo perimetral.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Set
import numpy as np

from src.common.constants import PERIMETER_SECTORS, SECTOR_COORDINATES, Sector


class DecisionType(str, Enum):
    """Categorías de decisión que puede tomar el sistema de evasión."""

    NO_THREAT = "SIN_AMENAZAS"              # Cuando no hay ningún objeto detectado
    SAFE_TRANSIT = "TRANSITO_SEGURO"        # Cuando los objetos pasan de lado sin chocar con la nave
    RED_ALERT = "ALERTA_ROJA_COLISION"      # Cuando un objeto apunta directamente hacia la nave


@dataclass
class EvasionDecision:
    """Estructura que contiene los resultados completos de la evaluación."""

    decision: DecisionType
    active_sectors: List[Sector]
    consecutive_groups: List[List[Sector]]
    isolated_sectors: List[Sector]
    explanation: str
    action_taken: str


class EvasionEvaluator:
    """Clase encargada de analizar la matriz 3x3 y determinar si hay peligro de colisión."""

    def __init__(self) -> None:
        """Carga la lista perimetral ordenada de los 8 sectores exteriores."""
        # El perímetro está ordenado en círculo: [NO, N, NE, E, SE, S, SO, O]
        self.perimeter = PERIMETER_SECTORS
        self.perimeter_len = len(PERIMETER_SECTORS)  # Son 8 sectores en total

    def evaluate(self, grid: np.ndarray) -> EvasionDecision:
        """Examina la cuadrícula 3x3 y toma una decisión de vuelo."""
        # Paso 1: Encontrar todos los sectores que tienen un 1 en la matriz
        active_sectors: List[Sector] = []
        for sector in self.perimeter:
            row, col = SECTOR_COORDINATES[sector]
            # Si el valor de la casilla es 1, se agrega a la lista de detecciones activas
            if grid[row, col] == 1:
                active_sectors.append(sector)

        total_active = len(active_sectors)

        # Caso 1 del documento: Cuando no hay ningún sector con valor 1 (matriz en ceros)
        if total_active == 0:
            return EvasionDecision(
                decision=DecisionType.NO_THREAT,
                active_sectors=[],
                consecutive_groups=[],
                isolated_sectors=[],
                explanation="Espacio circundante despejado. Sin detecciones en radar.",
                action_taken="Mantener curso estándar y velocidad nominal.",
            )

        # Paso 2: Convertir los sectores activos en sus posiciones numéricas en el círculo (del 0 al 7)
        active_indices = {self.perimeter.index(s) for s in active_sectors}
        visited_indices: Set[int] = set()
        consecutive_groups_indices: List[List[int]] = []

        # Paso 3: Agrupar sectores activos que sean vecinos inmediatos en el anillo perimetral
        for idx in active_indices:
            if idx in visited_indices:
                continue

            # Inicia un grupo nuevo para verificar qué vecinos están conectados
            group = []
            queue = [idx]
            visited_indices.add(idx)

            while queue:
                curr = queue.pop(0)
                group.append(curr)

                # Un sector tiene dos vecinos en el círculo: el anterior y el siguiente
                # El uso de % self.perimeter_len permite conectar el último sector (O, pos 7) con el primero (NO, pos 0)
                neighbors = [(curr - 1) % self.perimeter_len, (curr + 1) % self.perimeter_len]
                for n in neighbors:
                    # Si el vecino también tiene detección activa y no lo hemos visitado, se suma al grupo
                    if n in active_indices and n not in visited_indices:
                        visited_indices.add(n)
                        queue.append(n)

            # Guarda el grupo ordenado
            consecutive_groups_indices.append(sorted(group))

        # Paso 4: Separar los grupos en dos categorías: consecutivos (2 o más) y aislados (exactamente 1)
        consecutive_groups: List[List[Sector]] = []
        isolated_sectors: List[Sector] = []

        for grp in consecutive_groups_indices:
            sector_grp = [self.perimeter[i] for i in grp]
            if len(grp) >= 2:
                # Si hay 2 o más sectores contiguos encendidos, es una trayectoria tangencial continua
                consecutive_groups.append(sector_grp)
            else:
                # Si está solo, significa que es una amenaza directa hacia el centro
                isolated_sectors.append(sector_grp[0])

        # Caso 2 del documento: Si hay al menos un sector aislado con un 1
        # Esto significa que el meteorito no pasa de lado, sino que avanza directamente a la nave
        if isolated_sectors:
            sectors_str = ", ".join(s.value for s in isolated_sectors)
            return EvasionDecision(
                decision=DecisionType.RED_ALERT,
                active_sectors=active_sectors,
                consecutive_groups=consecutive_groups,
                isolated_sectors=isolated_sectors,
                explanation=f"Detección aislada en {sectors_str} indicando vector de impacto directo.",
                action_taken="Activar escudos reflectores y ejecutar propulsores de evasión inmediata.",
            )

        # Caso 3 del documento: Dos o más detecciones adyacentes continuas sin ninguna amenaza aislada
        # El objeto solo roza los radares exteriores en una trayectoria paralela o tangente
        if consecutive_groups and not isolated_sectors:
            groups_desc = "; ".join(
                f"[{', '.join(s.value for s in g)}]" for g in consecutive_groups
            )
            return EvasionDecision(
                decision=DecisionType.SAFE_TRANSIT,
                active_sectors=active_sectors,
                consecutive_groups=consecutive_groups,
                isolated_sectors=[],
                explanation=f"Trayectoria tangencial/paralela confirmada en secuencia de paso {groups_desc}.",
                action_taken="Registrar tránsito seguro de meteorito. Mantener rumbo sin alterar propulsión.",
            )

        # Caso de seguridad por precaución si ocurre algún patrón inesperado
        return EvasionDecision(
            decision=DecisionType.RED_ALERT,
            active_sectors=active_sectors,
            consecutive_groups=[],
            isolated_sectors=active_sectors,
            explanation="Patrón anómalo no clasificado de forma segura. Precaución máxima.",
            action_taken="Modo defensivo preventivo activado.",
        )
