"""Generador de números pseudoaleatorios con semilla compartida.

Este módulo implementa un algoritmo matemático (generador congruencial lineal) que produce
números que parecen aleatorios pero son 100% reproducibles si se utiliza la misma semilla.
Esto cumple con el objetivo de generar un entorno determinista entre procesos distribuidos.
"""

from typing import List


class SharedSeedPRNG:
    """Generador pseudoaleatorio determinista para coordinar la simulación."""

    # Valores matemáticos ampliamente utilizados (Numerical Recipes)
    DEFAULT_MULTIPLIER = 1664525
    DEFAULT_INCREMENT = 1013904223
    DEFAULT_MODULUS = 2**32  # 4294967296 (espacio de 32 bits)

    def __init__(
        self,
        seed: int = 30326271,
        multiplier: int = DEFAULT_MULTIPLIER,
        increment: int = DEFAULT_INCREMENT,
        modulus: int = DEFAULT_MODULUS,
    ) -> None:
        """Guarda la semilla inicial y los parámetros matemáticos."""
        self.initial_seed = seed
        # Asegura que el estado inicial no supere el módulo
        self.state = seed % modulus
        self.multiplier = multiplier
        self.increment = increment
        self.modulus = modulus

    def reset(self) -> None:
        """Reinicia el generador al estado de la semilla inicial."""
        self.state = self.initial_seed % self.modulus

    def next_int(self) -> int:
        """Calcula el siguiente número entero de la secuencia matemática.

        Fórmula congruencial: nuevo_estado = (multiplicador * estado_anterior + incremento) % modulo
        """
        self.state = (self.multiplier * self.state + self.increment) % self.modulus
        return self.state

    def next_float(self) -> float:
        """Convierte el número entero en un decimal entre 0.0 y 1.0 dividiendo entre el módulo."""
        return self.next_int() / self.modulus

    def next_uniform(self, low: float, high: float) -> float:
        """Genera un decimal dentro de un rango específico, por ejemplo entre 5.0 y 10.0."""
        return low + (high - low) * self.next_float()

    def next_choice(self, items: List[str]) -> str:
        """Elige un elemento de una lista de opciones de forma determinista."""
        # Multiplica el decimal obtenido por el tamaño de la lista para calcular la posición
        index = int(self.next_float() * len(items)) % len(items)
        return items[index]
