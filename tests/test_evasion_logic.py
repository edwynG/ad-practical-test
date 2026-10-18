"""Pruebas unitarias para la lógica de evasión y evaluación de la matriz 3x3.

¿Cómo funciona pytest en este archivo?
-------------------------------------
1. Descubrimiento automático: pytest busca archivos que comiencen por 'test_' (como este archivo).
2. Funciones de prueba: Cada función cuyo nombre empiece por 'test_' es ejecutada como una prueba individual.
3. Fixtures (@pytest.fixture): Son funciones que preparan datos u objetos reutilizables. Al poner el nombre
   del fixture como parámetro de una función de prueba, pytest se lo inyecta automáticamente.
4. Aserciones (assert): Se utiliza la palabra clave estándar de python 'assert condición'. Si la condición
   es verdadera la prueba pasa (se muestra en verde); si es falsa, pytest detiene la prueba y muestra
   exactamente qué valores fallaron.

Valida los 5 estados de ejemplo especificados en el documento oficial y casos límite adicionales.
"""

import numpy as np
import pytest

from src.common.constants import SECTOR_COORDINATES, Sector
from src.server.evasion_logic import DecisionType, EvasionEvaluator


# @pytest.fixture es un decorador de pytest que crea una instancia reutilizable del evaluador.
# Cada función de prueba que pida 'evaluator' recibirá una instancia limpia y nueva.
@pytest.fixture
def evaluator() -> EvasionEvaluator:
    """Prepara y devuelve una instancia limpia de EvasionEvaluator para cada prueba."""
    return EvasionEvaluator()


def make_grid_from_dict(active_dict: dict) -> np.ndarray:
    """Función de ayuda para construir una matriz 3x3 a partir de un diccionario de sectores."""
    # Crea una matriz de ceros de 3x3
    grid = np.zeros((3, 3), dtype=int)
    # Coloca un 1 en la fila y columna del sector indicado
    for sector, val in active_dict.items():
        row, col = SECTOR_COORDINATES[sector]
        grid[row, col] = val
    return grid


def test_estado_1_sin_amenazas(evaluator: EvasionEvaluator) -> None:
    """Verifica el estado 1 del documento oficial: sin detecciones en radar.

    Matriz esperada:
    [ 0 0 0 ]
    [ 0 x 0 ]
    [ 0 0 0 ]
    Resultado esperado: SIN_AMENAZAS.
    """
    # Matriz completamente en ceros (sin objetos espaciales)
    grid = np.zeros((3, 3), dtype=int)

    # El evaluador procesa la matriz
    decision = evaluator.evaluate(grid)

    # Con 'assert' comprobamos que el resultado coincida exactamente con lo esperado
    assert decision.decision == DecisionType.NO_THREAT
    # Comprobamos que no haya sectores activos reportados
    assert len(decision.active_sectors) == 0


def test_estado_2_amenaza_desde_n(evaluator: EvasionEvaluator) -> None:
    """Verifica el estado 2 del documento oficial: objeto desde el norte (N).

    Matriz esperada:
    [ 0 1 0 ]
    [ 0 x 0 ]
    [ 0 0 0 ]
    Resultado esperado: ALERTA_ROJA_COLISION (único 1 aislado apuntando a la nave).
    """
    # Activamos únicamente el sector Norte
    grid = make_grid_from_dict({Sector.N: 1})

    decision = evaluator.evaluate(grid)

    # Debe activar alerta roja porque es un único 1 aislado
    assert decision.decision == DecisionType.RED_ALERT
    # Comprobamos que el sector N figure en la lista de amenazas aisladas
    assert Sector.N in decision.isolated_sectors


def test_estado_3_transito_columna_este(evaluator: EvasionEvaluator) -> None:
    """Verifica el estado 3 del documento oficial: objeto en la columna este (NE, E).

    Matriz esperada:
    [ 0 0 1 ]
    [ 0 x 1 ]
    [ 0 0 0 ]
    Resultado esperado: TRANSITO_SEGURO (dos 1 consecutivos en el borde perimetral).
    """
    # Activamos los sectores vecinos Noreste y Este
    grid = make_grid_from_dict({Sector.NE: 1, Sector.E: 1})

    decision = evaluator.evaluate(grid)

    # Debe clasificarlo como tránsito seguro porque los sectores son adyacentes y no apuntan al centro
    assert decision.decision == DecisionType.SAFE_TRANSIT
    # No debe haber amenazas aisladas de colisión
    assert len(decision.isolated_sectors) == 0


def test_estado_4_amenaza_desde_o(evaluator: EvasionEvaluator) -> None:
    """Verifica el estado 4 del documento oficial: objeto desde el oeste (O).

    Matriz esperada:
    [ 0 0 0 ]
    [ 1 x 0 ]
    [ 0 0 0 ]
    Resultado esperado: ALERTA_ROJA_COLISION.
    """
    # Activamos únicamente el sector Oeste
    grid = make_grid_from_dict({Sector.O: 1})

    decision = evaluator.evaluate(grid)

    # Debe ser alerta roja por ser un 1 solitario
    assert decision.decision == DecisionType.RED_ALERT
    assert Sector.O in decision.isolated_sectors


def test_estado_5_amenaza_desde_no(evaluator: EvasionEvaluator) -> None:
    """Verifica el estado 5 del documento oficial: objeto desde el noroeste (NO).

    Matriz esperada:
    [ 1 0 0 ]
    [ 0 x 0 ]
    [ 0 0 0 ]
    Resultado esperado: ALERTA_ROJA_COLISION.
    """
    # Activamos únicamente el sector Noroeste
    grid = make_grid_from_dict({Sector.NO: 1})

    decision = evaluator.evaluate(grid)

    # Debe activar alerta roja de colisión
    assert decision.decision == DecisionType.RED_ALERT
    assert Sector.NO in decision.isolated_sectors


def test_caso_limite_envolvente_o_y_no(evaluator: EvasionEvaluator) -> None:
    """Verifica el caso límite de consecutividad entre los extremos del anillo (Oeste y Noroeste).

    En la lista perimetral circular, el sector O (índice 7) y el sector NO (índice 0) son vecinos contiguos.
    Por lo tanto, si ambos están activos juntos representan un paso perimetral seguro.
    """
    grid = make_grid_from_dict({Sector.O: 1, Sector.NO: 1})

    decision = evaluator.evaluate(grid)

    # Debe reconocer la adyacencia circular como tránsito seguro
    assert decision.decision == DecisionType.SAFE_TRANSIT


def test_caso_multiple_amenazas_aisladas(evaluator: EvasionEvaluator) -> None:
    """Verifica qué ocurre si hay dos objetos simultáneos que no son vecinos (Norte y Sur).

    Al estar en extremos opuestos, ambos son amenazas independientes que se dirigen a la nave.
    """
    grid = make_grid_from_dict({Sector.N: 1, Sector.S: 1})

    decision = evaluator.evaluate(grid)

    # Debe activar alerta roja porque ninguno de los dos es tangente al otro
    assert decision.decision == DecisionType.RED_ALERT
    assert Sector.N in decision.isolated_sectors
    assert Sector.S in decision.isolated_sectors
