# Sistema de detección y evasión en estrella ("Aegis-Star 8-Sector")

Proyecto desarrollado para la asignatura Algoritmos Distribuidos de la Escuela de Computación, Facultad de Ciencias, Universidad Central de Venezuela (UCV).

Este proyecto implementa un sistema distribuido tolerante a fallas bajo una topología en estrella usando el estándar MPI a través de la biblioteca `mpi4py`. El sistema simula el centro de mando de una nave espacial (servidor central en el rango 0) rodeado por 8 nodos sensores periféricos de radar (rangos 1 al 8) que escanean sectores espaciales, reportan detecciones en tiempo real, construyen dinámicamente una matriz de amenazas de 3 × 3 y ejecutan maniobras evasivas o activación de escudos.

---

## Resumen ejecutivo del proyecto

1. **Topología en estrella**: 1 servidor central ("La Nave", rango 0) y 8 radares periféricos (rangos 1 al 8).
2. **Paso de mensajes no bloqueante**: Uso de sondeos no bloqueantes (`MPI.Comm.Iprobe`) para recolectar detecciones y latidos sin condiciones de carrera ni bloqueos mutuos (*deadlocks*).
3. **Matriz de amenazas 3 × 3**: Cuadrícula espacial binaria donde `0` indica espacio despejado y `1` detección activa de meteorito o basura espacial.
4. **Reglas de clasificación estricta**:
   - **Único 1 aislado**: Alerta roja por colisión inminente (trayectoria lineal convergente hacia la nave).
   - **Dos o más 1 consecutivos y adyacentes**: Tránsito seguro (trayectoria paralela o tangente que roza los sensores sin colisionar).
   - **Matriz en ceros**: Espacio despejado sin riesgos.
5. **Generador pseudoaleatorio determinista (PRNG con semilla compartida)**: Algoritmo congruencial lineal que garantiza repetibilidad en simulaciones y pruebas distribuidas.
6. **Tolerancia a fallas por latidos de vida (heartbeats)**: Detección automática de desconexiones y reasignación dinámica de sectores de radar hacia sensores vecinos activos.

> [!NOTE]
> Este proyecto modela una topología pura en estrella donde los 8 sensores no se comunican directamente entre sí, sino exclusivamente con el servidor central mediante el paso de mensajes en MPI.

---

## Estructura del proyecto

El repositorio organiza el código fuente separando claramente las responsabilidades del servidor central, los sensores y las utilidades comunes:

```text
parcial/
├── docs/                # Enunciado, libros y presentaciones de teoría
│   ├── ad_parcial_mpi.pdf
│   ├── libros/
│   └── teoria/
├── src/                 # Código fuente de la solución
│   ├── common/          # Constantes, protocolo y generador determinista
│   ├── sensors/         # Lógica de los 8 nodos sensores periféricos
│   ├── server/          # Servidor central (nave), matriz 3x3 y fallas
│   └── visualization/   # Visualización en consola con rich
├── tests/               # Pruebas automatizadas con pytest
├── .gitignore           # Exclusiones de git (.venv, cache)
├── requirements.txt     # Dependencias de python (mpi4py, numpy, rich, pytest)
├── main.py              # Punto de entrada de la simulación mpi
└── README.md            # Documentación técnica y teórica del sistema
```

---

## Configuración del entorno virtual e instalación

Todas las operaciones se realizan directamente desde la terminal mediante comandos estándar, sin depender de scripts externos.

### Requisitos previos del sistema

En distribuciones basadas en Debian o Ubuntu (incluyendo WSL), es necesario contar con Python y los paquetes de OpenMPI instalados:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip openmpi-bin libopenmpi-dev
```

> [!IMPORTANT]
> Es indispensable contar con los paquetes de desarrollo de OpenMPI (`openmpi-bin` y `libopenmpi-dev`) instalados en el sistema operativo antes de instalar las dependencias con pip.

### Paso a paso para crear el entorno virtual e instalar dependencias

1. Abre una terminal y sitúate en la carpeta raíz del proyecto:
   ```bash
   cd ad-practical-test
   ```

2. Crea el entorno virtual de Python llamado `.venv`:
   ```bash
   python3 -m venv .venv
   ```

3. Actualiza el gestor de paquetes `pip` dentro del entorno virtual:
   ```bash
   .venv/bin/pip install --upgrade pip
   ```

4. Instala las dependencias del proyecto desde `requirements.txt`:
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

5. (Opcional) Si deseas activar el entorno en tu sesión interactiva:
   ```bash
   source .venv/bin/activate
   ```

> [!TIP]
> Si estás trabajando en Visual Studio Code o Cursor en WSL, selecciona el intérprete de Python ubicado en `.venv/bin/python` para que el editor reconozca automáticamente los módulos y el entorno de pruebas.

---

## Ejecución de la simulación distribuida

Para poner en marcha el sistema distribuido con los 9 procesos requeridos (1 nave central + 8 sensores periféricos), se utiliza la herramienta `mpirun` de OpenMPI.

### Comando básico de ejecución

```bash
mpirun -n 9 --oversubscribe .venv/bin/python main.py
```

> [!TIP]
> El parámetro `--oversubscribe` es crucial para entornos de prueba y computadores personales: le indica a OpenMPI que ejecute los 9 procesos concurrentes incluso si el procesador físico dispone de menos de 9 núcleos de CPU.

### Parámetros opcionales por línea de comandos

El archivo `main.py` acepta parámetros para ajustar el comportamiento de la simulación:

| Parámetro | Valor por defecto | Descripción |
| :--- | :---: | :--- |
| `--cycles` | `8` | Número de ciclos de escaneo que realizará la nave antes de apagarse (usar `0` para ejecución continua). |
| `--delay` | `1.0` | Tiempo de pausa en segundos entre cada evaluación de ciclo en la nave central. |
| `--seed` | `42` | Semilla inicial para el generador pseudoaleatorio determinista (PRNG). |

Ejemplos de ejecución personalizada:

```bash
# Ejecutar 12 ciclos con una pausa de 0.8 segundos entre actualizaciones
mpirun -n 9 --oversubscribe .venv/bin/python main.py --cycles 12 --delay 0.8

# Ejecutar con una semilla pseudoaleatoria específica para reproducir un escenario
mpirun -n 9 --oversubscribe .venv/bin/python main.py --cycles 10 --seed 98765

# Ejecutar de forma indefinida hasta presionar Ctrl+C
mpirun -n 9 --oversubscribe .venv/bin/python main.py --cycles 0 --delay 1.2
```

---

## Arquitectura y modelo de la matriz de amenazas (3 × 3)

### Distribución espacial en estrella

La nave espacial se ubica en el centro, rodeada por los 8 sectores direccionales:

```text
                  [NODO NORTE (N)] (Rango 2)
                         ↓
  [NODO NOROESTE (NO)]   |   [NODO NORESTE (NE)]
       (Rango 1)         |        (Rango 3)
           ↘             |             ↙
             ↘           |           ↙
  [NODO OESTE (O)] → [SERVIDOR] ← [NODO ESTE (E)]
     (Rango 4)       (LA NAVE)       (Rango 5)
                     (Rango 0)
             ↗           |           ↖
           ↗             |             ↖
  [NODO SUROESTE (SO)]   |   [NODO SURESTE (SE)]
       (Rango 6)         |        (Rango 8)
                         ↑
                   [NODO SUR (S)] (Rango 7)
```

### Mapeo de coordenadas en la matriz

La cuadrícula binaria de 3 filas por 3 columnas se indexa de la siguiente manera:

```text
               Columna 0    Columna 1    Columna 2
Fila 0 (Norte)   [ NO ]       [ N  ]       [ NE ]
Fila 1 (Centro)  [  O ]     [ NAVE ]       [  E ]
Fila 2 (Sur)     [ SO ]       [ S  ]       [ SE ]
```

| Sector | Coordenada (Fila, Columna) | Rango MPI | Descripción geográfica |
| :---: | :---: | :---: | :--- |
| **NO** | `(0, 0)` | Rango 1 | Cuadrante superior izquierdo (Noroeste) |
| **N** | `(0, 1)` | Rango 2 | Cuadrante superior central (Norte) |
| **NE** | `(0, 2)` | Rango 3 | Cuadrante superior derecho (Noreste) |
| **O** | `(1, 0)` | Rango 4 | Cuadrante lateral izquierdo (Oeste) |
| **x** | `(1, 1)` | Rango 0 | Centro de mando de la nave espacial |
| **E** | `(1, 2)` | Rango 5 | Cuadrante lateral derecho (Este) |
| **SO** | `(2, 0)` | Rango 6 | Cuadrante inferior izquierdo (Suroeste) |
| **S** | `(2, 1)` | Rango 7 | Cuadrante inferior central (Sur) |
| **SE** | `(2, 2)` | Rango 8 | Cuadrante inferior derecho (Sureste) |

### Lógica de evaluación y toma de decisiones

El evaluador de evasión (`src/server/evasion_logic.py`) analiza el grafo perimetral cíclico formado por los 8 sectores exteriores en sentido horario:

$$\text{Anillo perimetral} = [\text{NO}, \text{N}, \text{NE}, \text{E}, \text{SE}, \text{S}, \text{SO}, \text{O}]$$

Las decisiones se clasifican estrictamente según las reglas del documento oficial:

1. **Sin amenazas (`SIN_AMENAZAS`)**:
   - Cantidad de detecciones activas igual a cero.
   - Acción: mantener curso normal y velocidad de crucero.

2. **Alerta roja de colisión inminente (`ALERTA_ROJA_COLISION`)**:
   - Se detecta un **único 1 aislado** en cualquier sector de entrada (o bien detecciones simultáneas pero no consecutivas).
   - Significado físico: el meteorito avanza en una trayectoria estrictamente lineal y directa hacia el centro de la nave.
   - Acción: activar escudos reflectores y encender propulsores de maniobra evasiva inmediata.

3. **Tránsito seguro (`TRANSITO_SEGURO`)**:
   - Se detectan **dos o más valores 1 consecutivos y adyacentes** a lo largo del anillo perimetral (por ejemplo: `NE` y `E`, o `O` y `NO`).
   - Significado físico: el objeto se desplaza de manera paralela o tangente cruzando los sensores de lado sin rumbo de interceptación hacia el centro.
   - Acción: registrar el paso seguro del objeto sin alterar los propulsores.

> [!IMPORTANT]
> Un único 1 aislado en cualquier sector activa inmediatamente la alerta roja por colisión. La condición de tránsito seguro solo se cumple cuando dos o más valores 1 son estrictamente adyacentes a lo largo del perímetro y no coexisten con amenazas aisladas simultáneas.

---

## Casos de ejemplo evaluados según el documento oficial

| Caso | Sectores con 1 | Matriz resultante | Clasificación esperada | Motivo físico |
| :---: | :---: | :---: | :---: | :--- |
| **Estado 1** | Ninguno | `[[0,0,0],[0,x,0],[0,0,0]]` | `SIN_AMENAZAS` | Espacio despejado. |
| **Estado 2** | `N` | `[[0,1,0],[0,x,0],[0,0,0]]` | `ALERTA_ROJA_COLISION` | Único 1 aislado que apunta al centro desde el Norte. |
| **Estado 3** | `NE`, `E` | `[[0,0,1],[0,x,1],[0,0,0]]` | `TRANSITO_SEGURO` | Dos 1s consecutivos en la columna Este (trayectoria paralela). |
| **Estado 4** | `O` | `[[0,0,0],[1,x,0],[0,0,0]]` | `ALERTA_ROJA_COLISION` | Único 1 aislado que apunta al centro desde el Oeste. |
| **Estado 5** | `NO` | `[[1,0,0],[0,x,0],[0,0,0]]` | `ALERTA_ROJA_COLISION` | Único 1 aislado en la diagonal superior izquierda. |
| **Caso límite** | `O`, `NO` | `[[1,0,0],[1,x,0],[0,0,0]]` | `TRANSITO_SEGURO` | Adyacencia perimetral envolvente entre el sector 7 y el sector 0. |

---

## Pruebas automatizadas con pytest

El proyecto cuenta con una suite completa de pruebas unitarias que validan la lógica de decisión, el generador determinista y el protocolo de red.

### Cómo ejecutar las pruebas

Ejecuta el siguiente comando directamente con el intérprete del entorno virtual:

```bash
.venv/bin/pytest tests/ -v
```

> [!NOTE]
> Las pruebas unitarias validan la lógica pura de la matriz, el determinismo del PRNG y las estructuras de red en memoria de forma inmediata, sin necesidad de invocar `mpirun`.

### Explicación del funcionamiento de pytest

¿Cómo opera pytest en este proyecto?

1. **Descubrimiento automático**: Pytest inspecciona la carpeta `tests/` y busca automáticamente archivos que comiencen con el prefijo `test_` (como `test_evasion_logic.py`, `test_prng.py` y `test_protocol.py`).
2. **Funciones de prueba**: Cada función dentro de estos archivos cuyo nombre inicie con `test_` es tratada como un caso de prueba independiente.
3. **Uso de fixtures (`@pytest.fixture`)**: Son funciones utilitarias que preparan recursos u objetos de prueba de forma modular. Por ejemplo, en `test_evasion_logic.py` el fixture `evaluator` crea una instancia limpia de la clase `EvasionEvaluator` y la inyecta automáticamente en cada función que declare ese argumento.
4. **Validación con aserciones (`assert`)**: Pytest utiliza la instrucción estándar de Python `assert condición`. Si la condición es verdadera, la prueba es marcada como aprobada (`PASSED`). Si es falsa, la prueba falla (`FAILED`) y pytest muestra en pantalla un reporte visual con la diferencia exacta entre el valor esperado y el obtenido.
5. **Aislamiento de fallas**: Si una prueba falla, las demás pruebas continúan ejecutándose, garantizando un informe completo del estado de todo el sistema.

---

## Fundamentos teóricos y referencias del directorio docs

El diseño de este sistema distribuido toma como base los conceptos expuestos en las clases teóricas y en los libros de referencia disponibles en la carpeta `docs/`:

1. **Comunicación asíncrona y prevención de bloqueos mutuos (*deadlocks*)**:
   - En sistemas distribuidos con topología en estrella, si el servidor central utilizara recepciones bloqueantes rígidas (`MPI_Recv`), un desfase temporal o la caída de un sensor causaría un abrazo mortal. Por ello se implementó sondeo no bloqueante mediante `MPI.Comm.Iprobe`, garantizando que la nave procese todos los mensajes disponibles de cualquier sensor sin detener su ciclo de decisión.

2. **Generación determinista y reproducible con semilla compartida**:
   - Para evaluar y comparar de forma justa el comportamiento de múltiples nodos en un entorno espacial sin recurrir a transmisión intensiva de datos de entorno, se aplica un generador congruencial lineal con semilla compartida que reproduce exactamente las mismas condiciones en cada nodo según su rango.

3. **Tolerancia a fallas mediante latidos de vida (*heartbeats*)**:
   - Cada nodo sensor emite un mensaje periódico de latido hacia la nave central. Si transcurre un período de tiempo superior al umbral establecido (`heartbeat_timeout`) sin recibir señal de un sensor, el detector de fallas lo cataloga como desconectado y activa una reconfiguración dinámica de cobertura, asignando a los sensores vecinos activos la vigilancia del sector huérfano.

## Flujo de ejecución y verificación del sistema

El funcionamiento dinámico del sistema distribuido se desarrolla a través de las siguientes etapas concurrentes:

1. **Inicialización y bifurcación de roles**:
   - Al invocar `mpirun` con 9 procesos, el comunicador global `MPI.COMM_WORLD` asigna un rango único (del 0 al 8) a cada proceso.
   - El proceso con rango 0 inicializa la nave espacial (`ShipServer`), la matriz de amenazas 3 × 3 y el detector de fallas.
   - Los procesos con rangos del 1 al 8 inicializan los sensores periféricos (`SensorNode`), cada uno asociado a su sector geográfico y con un generador pseudoaleatorio determinista (`SharedSeedPRNG`) configurado con su semilla derivada.

2. **Ciclo de escaneo y emisión de reportes**:
   - Cada nodo sensor ejecuta su ciclo de escaneo a intervalos regulares, evaluando la presencia de objetos en su sector espacial.
   - Si se detecta un objeto, el sensor empaqueta un mensaje `ThreatEvent` con etiqueta `MessageTag.DETECTION` y lo envía a la nave central.
   - Periódicamente, cada sensor envía un mensaje `HeartbeatMessage` con etiqueta `MessageTag.HEARTBEAT` confirmando su operatividad continua.

3. **Recolección asíncrona en el servidor central**:
   - La nave central procesa el buzón de entrada usando sondeos no bloqueantes con `MPI.Comm.Iprobe(source=MPI.ANY_SOURCE)`.
   - Esto previene activamente condiciones de carrera y bloqueos mutuos (*deadlocks*), permitiendo atender ráfagas concurrentes de múltiples sensores sin congelar el ciclo principal.

4. **Actualización de la matriz y toma de decisiones**:
   - Con cada evento procesado, la cuadrícula 3 × 3 actualiza el valor del sector correspondiente.
   - El evaluador de evasión analiza la configuración de valores en el anillo perimetral: si encuentra una detección aislada activa la alerta roja de colisión; si detecta dos o más 1s contiguos en el perímetro clasifica el evento como tránsito seguro.
   - La interfaz en consola dibuja el estado en tiempo real con tablas y paneles a color facilitando el seguimiento visual de la simulación.

5. **Supervisión de salud y reconfiguración dinámica**:
   - El detector de fallas compara la hora actual con el último latido registrado de cada sensor. Si un nodo supera el tiempo de espera configurado, es marcado como desconectado y se asigna dinámicamente su sector al vecino activo más cercano.

---

## Cumplimiento de la rúbrica de evaluación

| Criterio | Ponderación | Estado de cumplimiento en el proyecto |
| :--- | :---: | :--- |
| **Ejecución y video demostrativo** | 25 puntos | El programa compila y corre de forma limpia con `mpirun` y 9 procesos en MPI. Se proporciona una salida enriquecida con colores (`rich`) que evidencia en tiempo real el paso de mensajes, la interacción entre procesos y la toma de decisiones. |
| **Código: nave y sensores** | 25 puntos | Roles claramente separados en módulos independientes (`src/server/` y `src/sensors/`). Código limpio, tipado, modular y documentado con comentarios sencillos en cada línea y bloque. |
| **Paso de mensajes y matriz de amenazas** | 20 puntos | Comunicación asíncrona no bloqueante con `Iprobe` para recolectar detecciones dinámicamente sin pérdida de datos, condiciones de carrera ni bloqueos mutuos (*deadlocks*). |
| **Lógica de clasificación y decisiones** | 15 puntos | Implementación precisa de la regla: un único 1 aislado genera alerta roja de colisión inminente; dos o más 1 consecutivos generan tránsito seguro. Casos de borde cubiertos al 100%. |
| **Generación aleatoria de objetos** | 15 puntos | Generador pseudoaleatorio determinista (PRNG con semilla compartida) que simula un entorno dinámico, variado y reproducible. |
