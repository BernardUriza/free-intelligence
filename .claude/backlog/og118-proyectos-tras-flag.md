# og118 Proyectos — escondido tras `OG118_PROYECTOS`, no borrado

Status: Dropped (apagado, con su rama cubierta por tests)
Apagado: 2026-08-29 por Bernard — *"desactiva todo lo de proyectos en og118 porque no lo uso"*, y después: *"tras config/env vars, así luego lo retomo"*

## Cómo se retoma

```bash
az containerapp update -n og118-api -g og118-rg --set-env-vars OG118_PROYECTOS=1
# y en el SWA del web: NEXT_PUBLIC_OG118_PROYECTOS=1
```

Nada que revertir, nada que reconstruir. Lee `apps/og118/DEPLOY.md` §
`OG118_PROYECTOS` antes de dejarlo prendido: hay dos huecos abiertos.

## Cómo está hecho el apagado

- **Las rutas no existen, no se rechazan.** Las 7 `/projects*` viven en un
  `projects_router` que `create_app()` monta sólo con el flag prendido, así que
  el 404 es real y no un handler consultando una variable.
- **El flag se lee AL LLAMAR** (`app.proyectos_activos()`), no al importar. Esa
  decisión no es estética: la primera versión usaba una constante de módulo, y
  probar la otra rama exigía `importlib.reload`, que en una sesión de pytest le
  derramó estado a siete tests de suites ajenas.
- **`corpus_id` se ignora, no se rechaza.** Una pestaña vieja que lo siga
  mandando conserva su chat; un 422 le rompería el chat entero por una feature
  que no pidió.
- **`rag_store` sale de las tools del turno**, y con él `delete_corpus` — una
  destructiva auto-aprobada que no tiene por qué seguir alcanzable para una
  feature que nadie usa.

## Lo que hace que esto no se pudra

`tests/test_projects_flag.py` afirma el interruptor en **las dos posiciones**, y
`tests/projects/` es la cobertura del lado encendido (5 suites que enciende su
propio conftest montando el router en la app compartida).

Esa cobertura fue la condición para esconder en vez de borrar, y la razón es un
precedente del mismo día: **el bug del corpus del 2026-08-29** —la subida
escribiendo en un HDF5 que la búsqueda ya no leía— existió porque
`get_rag_store()` tenía un `if OG118_BACKEND == "aire"` con un `else` que nadie
corría. Una rama apagada sin tests es esa trampa esperando a que alguien la
prenda. Ver [[both-ends-of-the-data-path]].

## Los dos huecos que hay que cerrar si vuelve

1. **La frontera del corpus no existe.** `corpus_id` lo teclea el MODELO en cada
   llamada; el binding del prompt pide, no impone (`build_runner` lo decía:
   *"es un addendum al prompt, no una frontera"*). El contrato ya está en
   fi-runner (`MCPServerSpec.pinned_args`) pero **ningún backend puede
   ejercerlo** hasta que la puerta de AIRE acepte el pin en el body del turno.
2. **`delete_corpus` se auto-aprueba** dentro de `rag_store`. Si vuelve, vuelve
   acotada.

## Nota de proceso

Se llegó aquí después de proponer —y empezar— el borrado completo (44 archivos,
4437 líneas). Bernard prefirió el flag para retomarlo después; la rama del
borrado se abandonó sin mergear. El argumento en contra del flag queda escrito
arriba (la rama apagada se pudre) y la mitigación también (los tests de las dos
ramas). Si algún día el mantenimiento del flag pesa más que la opción de
retomarlo, el borrado es un `git log` de distancia.
