"""Pruebas unitarias para el generador pseudoaleatorio determinista con semilla compartida.

¿Cómo funciona pytest en este archivo?
-------------------------------------
pytest ejecuta de manera independiente cada función cuyo nombre comience por 'test_'.
Dentro de cada función se evalúan expresiones con 'assert'. Si la igualdad o condición
falla, pytest detiene esa prueba específica y muestra en la terminal la diferencia exacta
entre el valor esperado y el obtenido. Si pasa sin errores, suma un punto verde al reporte final.
"""

from src.common.prng import SharedSeedPRNG


def test_prng_determinism() -> None:
    """Verifica que dos generadores independientes con la misma semilla produzcan la misma secuencia.

    Esto es fundamental en sistemas distribuidos para que dos nodos puedan reproducir
    el mismo entorno espacial de manera coordinada sin tener que enviarse cada número por la red.
    """
    # Creamos dos generadores distintos con la misma semilla (12345)
    prng_a = SharedSeedPRNG(seed=12345)
    prng_b = SharedSeedPRNG(seed=12345)

    # Generamos 20 números con cada uno
    seq_a = [prng_a.next_float() for _ in range(20)]
    seq_b = [prng_b.next_float() for _ in range(20)]

    # Comprobamos con assert que ambas listas de números sean idénticas
    assert seq_a == seq_b


def test_prng_reset() -> None:
    """Verifica que el método reset() reinicie la secuencia desde el principio con exactitud."""
    prng = SharedSeedPRNG(seed=999)

    # Primera pasada de 10 números
    first_pass = [prng.next_int() for _ in range(10)]

    # Reiniciamos el generador
    prng.reset()

    # Segunda pasada de 10 números
    second_pass = [prng.next_int() for _ in range(10)]

    # Ambas pasadas deben ser exactamente iguales
    assert first_pass == second_pass


def test_prng_uniform_range() -> None:
    """Verifica que la función next_uniform genere números estrictamente dentro del rango solicitado."""
    prng = SharedSeedPRNG(seed=777)

    # Probamos 50 valores en el rango [5.0, 15.0]
    for _ in range(50):
        val = prng.next_uniform(5.0, 15.0)
        # Comprobamos que el número nunca sea menor a 5.0 ni mayor a 15.0
        assert 5.0 <= val <= 15.0
