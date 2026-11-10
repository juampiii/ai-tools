# LangGraph desde DevFlow · Parte 1: los fundamentos

Cuaderno de estudio basado en el código real de `start-branch` y `commit-message`.

**Cómo usarlo.** Cada capítulo tiene tres partes: la teoría (con una analogía de .NET), el código real de DevFlow y unos ejercicios. Los ejercicios son de tres tipos:

- **Predice**: se responde con lápiz, sin ejecutar nada.
- **Comprueba**: se hace delante del ordenador, con el debugger o un `print`.
- **Modifica**: un cambio pequeño en el código para aplicar el concepto.

Las soluciones están al final. Intenta no mirarlas antes de tiempo.

---

## 0. Python mínimo para leer este código

Cuatro cosas de Python aparecen en todos los archivos. Si las entiendes, el resto se lee mucho mejor.

**`TypedDict`.** Es un `dict` normal con tipos para el analizador estático (ruff, Pylance). En runtime no hay clase ni validación: es un diccionario.

```python
class StartBranchState(TypedDict, total=False):
    card_id: int
    card_title: str
```

`total=False` significa que todas las claves son opcionales. En .NET sería como un record con todas las propiedades nullable.

**`dict.get` frente a `dict[...]`.** `state["card_title"]` lanza `KeyError` si la clave no existe. `state.get("feedback")` devuelve `None`. En el código verás `[...]` cuando el dato tiene que existir y `.get(...)` cuando puede faltar.

**Closures.** Una función definida dentro de otra "recuerda" las variables de la función exterior:

```python
def make_read_card(tracker: TrackerClient) -> Node:
    def read_card(state: StartBranchState) -> dict[str, Any]:
        card = tracker.get_card(state["card_id"])  # usa `tracker` de fuera
        ...

    return read_card
```

`make_read_card` es una factory. Devuelve una función que ya lleva el `tracker` dentro. En .NET es lo mismo que una lambda que captura una variable.

**`Protocol`.** `TrackerClient`, `GitClient` y `LlmClient` son `Protocol`: el equivalente a una `interface` de C#. La diferencia es que en Python una clase no declara que implementa el protocolo. Basta con que tenga los métodos (*duck typing* con comprobación estática).

---

## 1. Workflow frente a agent

LangGraph sirve para dos tipos de programas:

- **Workflow**: tú decides los pasos y su orden. El LLM, si aparece, es una herramienta más dentro de un paso.
- **Agent**: el LLM decide qué paso viene después y qué herramientas usar.

Los dos grafos de DevFlow son **workflows**. El LLM solo genera texto (un slug o un mensaje de commit). Nunca decide el camino. Esto es importante para leer el código: todas las decisiones están en funciones de Python que puedes leer y testear.

El grafo de `start-branch`:

```
START
  │
  ▼
read_card ──(error)──────────────────────────┐
  │                                          │
  ▼                                          │
resolve_prefix ──(error)─────────────────────┤
  │                                          │
  ▼                                          │
git_fetch ──(error)──────────────────────────┤
  │                                          │
  ▼                                          │
propose_name ◄────────────┐ (reject)         │
  │  └──(error)───────────┼──────────────────┤
  ▼                       │                  │
human_review ─────────────┘                  │
  │  └──(error)──────────────────────────────┤
  ▼ (approve / edit)                         │
create_branch ───────────────────────────► END
```

`commit-message` tiene la misma forma: `read_branch` → `read_changes` → `propose_message` ⇄ `human_review` → `copy_message`.

---

## 2. State

**Teoría.** El state es el único dato que recorre el grafo. Cada node lo lee y propone cambios. Piensa en un DTO compartido por todos los pasos de un pipeline, o en el `HttpContext` de ASP.NET, pero solo con datos.

**En tu código** (`start_branch/state.py`):

```python
class StartBranchState(TypedDict, total=False):
    card_id: int  # entrada
    card_title: str  # resultados intermedios
    card_type: str
    branch_prefix: str
    branch_name: str
    branch_slug: str
    rejected_slugs: list[str]
    feedback: str | None
    review_action: str
    created_branch: str  # resultado final
    llm_input_tokens: int  # métricas
    llm_output_tokens: int
    llm_cost: float
    error: str | None  # control de errores
```

Tres ideas de diseño que se repiten en DevFlow:

1. El state solo tiene **datos**. Los clientes (git, LLM, tracker) no están aquí. Llegan por las factories (capítulo 3).
2. Hay un campo `error`. Un node que falla escribe el mensaje ahí en lugar de lanzar una excepción. Después, el routing decide terminar (capítulo 6).
3. El grafo arranca con un state casi vacío: `graph.invoke({"card_id": card_id}, config)`. El resto de claves las van rellenando los nodes.

### Ejercicios

- **E2.1 · Predice.** ¿Por qué `error` vive en el state y no se usa `raise`? Piensa qué pasaría en el CLI si `git_fetch` lanzara una excepción.
- **E2.2 · Predice.** Justo después de `invoke`, antes de que se ejecute ningún node, ¿qué claves tiene el state de `commit-message`? Mira `commit_message/cli.py`, función `run`.

---

## 3. Node

**Teoría.** Un node es una función normal con esta firma:

```
(state) -> dict con SOLO las claves que cambian
```

Un node no devuelve el state completo y no modifica el que recibe. Tampoco sabe qué node viene después. Es como un handler de MediatR: recibe una entrada, hace su trabajo y devuelve un resultado. No conoce el pipeline.

**En tu código.** El node más simple, `resolve_prefix`, no tiene dependencias:

```python
def resolve_prefix(state: StartBranchState) -> dict[str, Any]:
    card_type = state["card_type"]
    prefix = BRANCH_PREFIXES.get(card_type)
    if prefix is None:
        supported = ", ".join(BRANCH_PREFIXES)
        return {"error": f"Unsupported card type: '{card_type}'. Supported: {supported}."}
    return {"branch_prefix": prefix}
```

Devuelve `{"branch_prefix": ...}` o `{"error": ...}`. Nada más.

Los nodes que necesitan un cliente externo se crean con una factory. Es la inyección de dependencias del proyecto:

```python
def make_git_fetch(git: GitClient, base_branch: str) -> Node:
    def git_fetch(state: StartBranchState) -> dict[str, Any]:
        try:
            git.fetch(REMOTE, base_branch)
        except ClientError as exc:
            return {"error": str(exc)}
        return {}

    return git_fetch
```

Fíjate en el `return {}`: el fetch no produce datos, así que el node no cambia nada del state.

Las factories se llaman al construir el grafo, en `graph.py`:

```python
builder.add_node("read_card", make_read_card(tracker))  # factory: lleva el tracker dentro
builder.add_node("resolve_prefix", resolve_prefix)  # función directa: no necesita nada
```

En .NET sería inyección por constructor. En los tests se pasa un `FakeTrackerClient` y el node no nota la diferencia.

### Ejercicios

- **E3.1 · Predice.** La carta es de tipo `"Bug"`. ¿Qué devuelve `resolve_prefix`? ¿Qué claves tiene el state completo después de este node?
- **E3.2 · Predice.** ¿Por qué `human_review` no tiene factory (`make_human_review`) y `propose_name` sí?

---

## 4. Cómo se mezcla el state: updates y reducers

**Teoría.** Cuando un node devuelve `{"branch_prefix": "bugfix/"}`, LangGraph mezcla ese dict con el state actual. Para cada clave usa una regla:

- **Por defecto: sobrescribir.** El valor nuevo reemplaza al anterior. Las claves que el node no devuelve no cambian.
- **Con reducer: combinar.** Un reducer es una función `(valor_actual, valor_nuevo) -> valor_final`. Se declara en el state con `Annotated`:

```python
from typing import Annotated
import operator


class MyState(TypedDict, total=False):
    items: Annotated[list[str], operator.add]  # actual + nuevo
```

Con este reducer, si un node devuelve `{"items": ["b"]}` y el state tenía `["a"]`, el resultado es `["a", "b"]`. El node solo devuelve lo que añade.

Analogía .NET: sin reducer, `dict[key] = value`. Con reducer, `dict[key] = Combine(dict[key], value)`.

**En tu código.** DevFlow **no usa reducers**. Todas las claves se sobrescriben. Por eso los nodes acumulan a mano:

```python
# human_review, en el rechazo
"rejected_slugs": [*state.get("rejected_slugs", []), state["branch_slug"]],

# propose_name, contadores de tokens y coste
"llm_input_tokens": state.get("llm_input_tokens", 0) + result.input_tokens,
"llm_cost": state.get("llm_cost", 0.0) + result.cost,
```

El node lee el valor actual, le suma lo nuevo y devuelve el total. Funciona, pero es justo el trabajo que hace un reducer. (`[*lista, x]` crea una lista nueva con los elementos de `lista` y `x` al final.)

### Ejercicios

- **E4.1 · Predice.** El usuario rechaza dos veces (slugs `fix-login` y `login-error-fix`) y aprueba la tercera. ¿Qué contiene `rejected_slugs` al final?
- **E4.2 · Modifica.** Cambia `rejected_slugs` a un reducer con `operator.add` y simplifica `human_review` para que solo devuelva el slug nuevo. Ejecuta `uv run pytest` para comprobar que todo sigue en verde.
- **E4.3 · Predice (la trampa).** Imagina que añades el reducer de E4.2 pero **olvidas** cambiar el node, que sigue devolviendo `[*state.get("rejected_slugs", []), slug]`. Con dos rechazos (`a` y después `b`), ¿qué contiene la lista?

---

## 5. StateGraph, START, END y edges

**Teoría.** El grafo se construye en dos fases: primero lo describes con un builder y después lo compilas (capítulo 7). Es el mismo patrón que `WebApplication.CreateBuilder()` → `builder.Build()`.

- `StateGraph(MiState)`: crea el builder y le dice qué forma tiene el state.
- `add_node("nombre", función)`: registra un node con un nombre.
- `add_edge("a", "b")`: después de `a`, siempre va `b`.
- `START` y `END`: dos nodes especiales. `START` es la entrada del grafo y `END` la salida.

**En tu código** (`start_branch/graph.py`, simplificado):

```python
def build_graph(tracker, llm, git, checkpointer, base_branch) -> CompiledStateGraph:
    builder = StateGraph(StartBranchState)

    builder.add_node("read_card", make_read_card(tracker))
    builder.add_node("resolve_prefix", resolve_prefix)
    # ... resto de nodes

    builder.add_edge(START, "read_card")  # el grafo siempre empieza aquí
    # ... conditional edges (capítulo 6)
    builder.add_edge("create_branch", END)  # después de crear la rama, termina

    return builder.compile(checkpointer=checkpointer)
```

Solo hay dos edges fijos: la entrada y la salida. Todos los demás son condicionales, porque después de casi cada node hay que mirar si hubo error.

`build_graph` recibe todas las dependencias como parámetros. Es la *composition root*: el CLI le pasa los clientes reales y los tests le pasan fakes.

### Ejercicios

- **E5.1 · Comprueba.** Dibuja en papel el grafo de `commit-message` leyendo solo `commit_message/graph.py`. Después compáralo con lo que genera LangGraph. Ejecuta esto en un script o en el debugger, con el grafo ya construido:

  ```python
  print(graph.get_graph().draw_mermaid())
  ```

  Pega la salida en <https://mermaid.live> para verla dibujada.

---

## 6. Conditional edges y ciclos

**Teoría.** Un conditional edge decide el siguiente node en tiempo de ejecución:

```python
builder.add_conditional_edges("origen", routing_function, ["destino_a", "destino_b", END])
```

- La **routing function** recibe el state y devuelve el **nombre** del siguiente node (un `str`).
- La lista final son los destinos posibles. LangGraph la usa para validar el grafo y para dibujarlo.

Las routing functions deben ser puras: leen el state y devuelven un nombre. No llaman a clientes ni cambian nada. Analogía .NET: un `switch` que devuelve el siguiente handler, o un middleware que hace *short-circuit*.

**En tu código** (`start_branch/routing.py`). Casi todas las routings hacen lo mismo:

```python
def _next_or_end(state: StartBranchState, next_node: str) -> str:
    return END if state.get("error") else next_node


def route_after_read_card(state: StartBranchState) -> str:
    return _next_or_end(state, "resolve_prefix")
```

Si hay error, termina. Si no, continúa. La interesante es la que va después de `human_review`:

```python
def route_after_human_review(state: StartBranchState) -> str:
    if state.get("error"):
        return END
    if state.get("review_action") == "reject":
        return "propose_name"  # vuelve atrás: esto crea un ciclo
    return "create_branch"
```

Si el usuario rechaza, el grafo **vuelve** a `propose_name`. Esto es un **ciclo**, y es lo que diferencia un grafo de una cadena lineal. El ciclo funciona porque el state guarda `feedback` y `rejected_slugs`. En la segunda vuelta, `propose_name` los lee y genera un prompt distinto.

Fíjate también en que `edit` no tiene rama propia. Va a `create_branch` igual que `approve`, porque `human_review` ya escribió el nombre editado en `branch_name`.

### Ejercicios

- **E6.1 · Predice.** La carta es de tipo `"Task"`. Escribe la lista de nodes que se ejecutan, en orden. ¿Se llama a git alguna vez? (Después busca el test `test_unsupported_card_type_ends_with_error_and_does_not_call_git` en `tests/start_branch/test_graph.py`.)
- **E6.2 · Predice.** ¿Qué pasaría si `route_after_human_review` no comprobara `error` primero, y el usuario edita el nombre y lo deja vacío?

---

## 7. `compile()` e `invoke()`

**Teoría.**

- `builder.compile(...)` valida el grafo y devuelve un `CompiledStateGraph`. Por ejemplo, comprueba que los edges apuntan a nodes que existen. El grafo compilado ya no se puede modificar. Es el `builder.Build()` de .NET.
- `graph.invoke(input, config)` ejecuta el grafo y devuelve el **state final** como un `dict`.

`invoke` termina por uno de dos motivos:

1. El grafo llega a `END`. Devuelve el state final.
2. Un node llama a `interrupt()` (capítulo 9). Devuelve el state de ese momento **más** una clave especial, `__interrupt__`.

**En tu código** (`start_branch/cli.py`, función `run`):

```python
config = {"configurable": {"thread_id": str(uuid4())}}
result = graph.invoke({"card_id": card_id}, config)

while "__interrupt__" in result:
    decision = review(result["__interrupt__"][0].value)
    result = graph.invoke(Command(resume=decision), config)

if error := result.get("error"):
    print(f"Error: {error}", file=sys.stderr)
    return 1
```

El bucle `while` es el corazón del CLI: mientras el grafo esté pausado, pregunta al usuario y reanuda. Cuando sale del bucle, el grafo ha terminado, con éxito o con error. (`:=` asigna y comprueba a la vez, como `if (x is { } error)` en C#.)

### Ejercicios

- **E7.1 · Predice.** El usuario aprueba a la primera. ¿Cuántas veces se llama a `graph.invoke` en total?

---

## 8. Checkpointer y `thread_id`

**Teoría.** El checkpointer guarda una foto del state después de cada paso del grafo. Gracias a eso, un grafo puede pararse y continuar más tarde desde el mismo punto.

- `InMemorySaver`: guarda las fotos en memoria. Se pierden al cerrar el proceso. Para un CLI es suficiente.
- Existen checkpointers en SQLite o Postgres para guardar las fotos entre ejecuciones.

El **`thread_id`** identifica una ejecución. Todas las fotos de una ejecución se guardan bajo el mismo `thread_id`. Analogía .NET: el *instance id* de una orquestación de Durable Functions, o un *correlation id*.

**En tu código.** El checkpointer se pasa al compilar:

```python
# cli.py
graph = build_graph(..., checkpointer=InMemorySaver(), ...)

# graph.py
return builder.compile(checkpointer=checkpointer)
```

Y el `thread_id` va en el `config` de **cada** `invoke`:

```python
config = {"configurable": {"thread_id": str(uuid4())}}
```

Sin checkpointer, `interrupt()` no funciona: no habría dónde guardar el punto de pausa.

### Ejercicios

- **E8.1 · Predice.** ¿Qué pasaría si el CLI generara un `uuid4()` nuevo dentro del bucle `while`, en cada `invoke`?
- **E8.2 · Comprueba.** Pon un breakpoint justo después del primer `graph.invoke` en `run`. Evalúa `graph.get_state(config).next` y `graph.get_state(config).values`. ¿Qué node está pendiente? ¿Qué claves tiene ya el state?

---

## 9. `interrupt()` y `Command(resume=...)`

**Teoría.** Esto es el *human-in-the-loop*: el grafo se para, una persona decide y el grafo continúa con esa decisión.

1. Un node llama a `interrupt(payload)`. El `payload` es lo que se quiere enseñar al usuario.
2. El grafo se para. El checkpointer guarda el state. `invoke` devuelve el state con `__interrupt__`.
3. El CLI lee `result["__interrupt__"][0].value` (el payload), pregunta al usuario y llama a `graph.invoke(Command(resume=decisión), config)` con el **mismo** `thread_id`.
4. LangGraph **vuelve a ejecutar el node desde la primera línea**. Esta vez `interrupt()` no se para: devuelve la decisión.

El punto 4 es lo que más confunde. El node no "continúa" desde la línea del `interrupt`. Se ejecuta otra vez entero. Es como el *replay* de una orquestación de Durable Functions: el código se repite y la llamada que ya tiene resultado lo devuelve directamente.

**En tu código** (`start_branch/nodes.py`, simplificado):

```python
def human_review(state: StartBranchState) -> dict[str, Any]:
    # This node reruns from the start on resume: no side effects before the interrupt.
    decision = interrupt({"card_title": state["card_title"], "branch_name": state["branch_name"]})

    action = decision.get("action")
    if action == "approve":
        return {"review_action": "approve"}
    if action == "edit":
        ...
        return {"review_action": "edit", "branch_name": edited_name}
    if action == "reject":
        return {"review_action": "reject", "feedback": ..., "rejected_slugs": [...]}
    return {"error": f"Unknown review action: {action!r}."}
```

- Primera ejecución: llega a `interrupt(...)` y se para. Nada de lo que hay debajo se ejecuta.
- Segunda ejecución (después de `Command(resume=...)`): `interrupt(...)` devuelve el dict de la decisión, por ejemplo `{"action": "reject", "feedback": "más corto"}`, y el node termina normalmente.

El comentario del código explica la regla más importante: **nada con efectos secundarios antes del `interrupt`**, porque se ejecutaría dos veces. Por eso el node que crea la rama (`create_branch`) es otro node distinto, después de la revisión.

Otro detalle: la decisión es un dict con una forma fija (`action`, `branch_name`, `feedback`), no texto libre. El node no necesita interpretar lo que escribe el usuario. Eso lo hace `prompt_review` en el CLI.

### Ejercicios

- **E9.1 · Predice.** El usuario rechaza una vez y aprueba la segunda. ¿Cuántas veces **empieza** a ejecutarse `human_review`? ¿Y `propose_name`? ¿Cuántas llamadas al LLM hay?
- **E9.2 · Predice.** Alguien mueve `git.create_branch(...)` dentro de `human_review`, antes del `interrupt`. ¿Qué pasa?
- **E9.3 · Comprueba.** Pon un `print("human_review start")` en la primera línea de `human_review`, ejecuta `uv run start-branch <id>`, rechaza una vez y aprueba. Compara con tu respuesta de E9.1. Quita el `print` después.

---

## 10. Todo junto: una ejecución paso a paso

Ejecución de `start-branch 12345` para una carta `Bug` titulada "Fix login error". El usuario rechaza la primera propuesta con el feedback "más corto" y aprueba la segunda.

| Paso | Qué se ejecuta | Qué cambia en el state |
|---|---|---|
| 1 | `invoke({"card_id": 12345})` | `card_id` |
| 2 | `read_card` | `card_title`, `card_type = "Bug"` |
| 3 | `resolve_prefix` | `branch_prefix = "bugfix/"` |
| 4 | `git_fetch` | nada (`{}`) |
| 5 | `propose_name` (LLM #1) | `branch_slug`, `branch_name`, tokens y coste |
| 6 | `human_review` → `interrupt` | nada. `invoke` vuelve con `__interrupt__` |
| 7 | CLI: el usuario rechaza → `invoke(Command(resume=...))` | |
| 8 | `human_review` otra vez, desde el principio | `review_action = "reject"`, `feedback`, `rejected_slugs` |
| 9 | `route_after_human_review` → `propose_name` | |
| 10 | `propose_name` (LLM #2, con feedback y slugs rechazados) | `branch_slug`, `branch_name`, tokens y coste acumulados |
| 11 | `human_review` → `interrupt` | nada. `invoke` vuelve con `__interrupt__` |
| 12 | CLI: el usuario aprueba → `invoke(Command(resume=...))` | |
| 13 | `human_review` otra vez | `review_action = "approve"` |
| 14 | `create_branch` | `created_branch` |
| 15 | `END` → `invoke` devuelve el state final | |

Si entiendes cada fila de esta tabla y por qué ocurre, has entendido la parte 1.

---

## Soluciones

**E2.1.** Con una excepción, el grafo se rompe a mitad y el CLI tendría que capturarla, sin un state final coherente. Con `error` en el state, el node termina normal, la routing lo ve y va a `END`, e `invoke` devuelve un state que el CLI sabe leer. El flujo de errores también es parte del grafo y se puede testear con las routing functions.

**E2.2.** Solo `min_length` y `max_length`: es el input de `graph.invoke({"min_length": ..., "max_length": ...}, config)`.

**E3.1.** Devuelve `{"branch_prefix": "bugfix/"}`. El state completo tiene `card_id`, `card_title`, `card_type` y `branch_prefix`.

**E3.2.** `human_review` no usa ningún cliente externo: solo el state e `interrupt`. `propose_name` necesita el `LlmClient`, y la factory es la forma de inyectárselo.

**E4.1.** `["fix-login", "login-error-fix"]`. La tercera propuesta se aprueba, así que no se añade.

**E4.2.** En `state.py`:

```python
from typing import Annotated, TypedDict
import operator


class StartBranchState(TypedDict, total=False):
    ...
    rejected_slugs: Annotated[list[str], operator.add]
```

En `human_review`, la rama de rechazo:

```python
"rejected_slugs": [state["branch_slug"]],
```

Los contadores de tokens se pueden pasar a `Annotated[int, operator.add]` y `Annotated[float, operator.add]` de la misma forma. El node devuelve entonces `result.input_tokens` sin sumar.

**E4.3.** `["a", "a", "b"]`. Primer rechazo: el node devuelve `["a"]` y el reducer hace `[] + ["a"] = ["a"]`. Segundo rechazo: el node devuelve `["a", "b"]` (ya acumulado a mano) y el reducer hace `["a"] + ["a", "b"]`. El reducer y la acumulación manual suman dos veces.

**E5.1.** `START → read_branch → read_changes → propose_message → human_review → copy_message → END`, con `human_review → propose_message` (rechazo) y salidas a `END` desde `read_branch`, `read_changes`, `propose_message` y `human_review` cuando hay error.

**E6.1.** `read_card` → `resolve_prefix` → `END`. `resolve_prefix` devuelve `error` y `route_after_resolve_prefix` va a `END`. `git_fetch` nunca se ejecuta, así que git no se llama.

**E6.2.** `human_review` devuelve `{"error": "The edited branch name is empty."}` sin `review_action`. Sin el `if error`, la routing mira el `review_action` que haya en el state. Si es la primera revisión, no hay ninguno y va a `create_branch` con el `branch_name` anterior: se crearía una rama que el usuario no ha aprobado. Si antes hubo un rechazo, `review_action` sigue valiendo `"reject"` (nadie lo ha sobrescrito, capítulo 4) y vuelve a `propose_name`. Por eso `error` se comprueba siempre primero.

**E7.1.** Dos: el `invoke` inicial (que vuelve con `__interrupt__`) y el `invoke` con `Command(resume=...)`.

**E8.1.** El `invoke` de reanudar iría a un thread nuevo, sin fotos guardadas. No hay ninguna pausa que reanudar en ese thread, así que la ejecución original nunca continúa. El `thread_id` tiene que ser el mismo en toda la ejecución.

**E8.2.** `next` es `("human_review",)`: el node que está pausado. `values` tiene todo lo calculado hasta `propose_name`: `card_id`, `card_title`, `card_type`, `branch_prefix`, `branch_name`, `branch_slug` y los contadores del LLM.

**E9.1.** `human_review` empieza 4 veces: 2 por cada revisión (una se para en el `interrupt` y otra se reanuda). `propose_name` se ejecuta 2 veces, y por eso hay 2 llamadas al LLM.

**E9.2.** La rama se intentaría crear dos veces: una antes de la pausa y otra al reanudar. La segunda fallaría porque la rama ya existe. Además, se crearía antes de que el usuario la apruebe.

**E9.3.** Verás `human_review start` cuatro veces, igual que en E9.1.
