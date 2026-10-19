"""Visualización en terminal en tiempo real con rich.

Genera paneles visuales para la matriz de 3x3, estado de salud de sensores y decisiones de evasión,
facilitando la grabación de la demostración para evaluación.
"""

from typing import Dict
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.common.constants import Sector
from src.server.evasion_logic import DecisionType, EvasionDecision


class ConsoleDisplay:
    """Gestiona la salida formateada en consola usando la librería rich."""

    def __init__(self) -> None:
        """Crea el objeto de consola de rich para poder dibujar tablas y paneles con colores."""
        self.console = Console()

    def render_dashboard(
        self,
        grid: np.ndarray,
        decision: EvasionDecision,
        sensor_status: Dict[Sector, bool],
        cycle_number: int,
    ) -> None:
        """Imprime un tablero completo con la cuadrícula de amenazas y el estado del sistema."""
        # Crea la tabla de 3 columnas para la matriz de radar
        matrix_table = Table(title="Radar espacial (3 x 3)", show_header=True, header_style="bold cyan")
        matrix_table.add_column("Oeste", justify="center")
        matrix_table.add_column("Centro", justify="center")
        matrix_table.add_column("Este", justify="center")

        # Nombres de los sectores según su posición en la matriz
        labels = [
            ["NO", "N", "NE"],
            ["O", "NAVE", "E"],
            ["SO", "S", "SE"],
        ]

        # Recorre cada una de las 3 filas
        for r in range(3):
            row_cells = []
            for c in range(3):
                # Casilla central: aquí se encuentra la nave espacial
                if r == 1 and c == 1:
                    row_cells.append("[bold white on blue] NAVE (x) [/]")
                else:
                    val = grid[r, c]
                    lbl = labels[r][c]
                    # Si el sensor tiene detección activa (1)
                    if val == 1:
                        # Si es colisión se pinta en rojo brillante, si es tránsito seguro en verde
                        if decision.decision == DecisionType.RED_ALERT:
                            style = "bold white on red"
                        else:
                            style = "bold black on green"
                        row_cells.append(f"[{style}] {lbl}: 1 [/]")
                    else:
                        # Si está en 0 se muestra atenuado (despejado)
                        row_cells.append(f"[dim]{lbl}: 0[/dim]")
            matrix_table.add_row(*row_cells)

        # Selecciona el color del borde y título según la severidad de la decisión
        decision_color = {
            DecisionType.NO_THREAT: "cyan",
            DecisionType.SAFE_TRANSIT: "green",
            DecisionType.RED_ALERT: "bold red",
        }[decision.decision]

        # Prepara el texto del informe con lenguaje simple y directo
        decision_text = Text()
        decision_text.append(f"Paso de escaneo: {cycle_number}\n", style="bold")
        decision_text.append(f"Situación: {decision.decision.value}\n", style=decision_color)
        decision_text.append(f"Detalle: {decision.explanation}\n", style="italic")
        decision_text.append(f"Acción: {decision.action_taken}", style="bold yellow")

        # Construye la barra de estado de vida de los 8 sensores
        sensors_text = Text()
        for sector, active in sensor_status.items():
            status_symbol = "●" if active else "✖"
            style = "green" if active else "red"
            sensors_text.append(f"{sector.value}: {status_symbol}  ", style=style)

        # Imprime separador y los 3 paneles en la terminal
        self.console.print("\n" + "=" * 65)
        self.console.print(Panel(matrix_table, title="Radar de la nave", border_style="cyan"))
        self.console.print(Panel(decision_text, title="Decisión de la nave", border_style=decision_color))
        self.console.print(Panel(sensors_text, title="Estado de los sensores (en línea)", border_style="blue"))
