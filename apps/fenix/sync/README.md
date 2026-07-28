# Sincronización claude.ai → fenix

Mientras el equipo de la papelería siga trabajando en el Project de claude.ai
("Servicios Papeleros Fénix"), esa es la fuente de verdad y fenix es el espejo.
Cuando fenix se lance con su propia API key, la dirección se invierte y esta
carpeta se borra.

**Regla:** el espejo se actualiza SÓLO por este camino. Nadie sube documentos al
corpus de fenix a mano — un doc subido fuera del script queda invisible para
`estado.json`, y la siguiente sincronización lo duplicará con otro nombre. (Ya
pasó una vez el 27-jul y hubo que recrear el corpus.)

## El ritual (cuando Bernard dice "sincroniza")

**1. Exportar el estado de claude.ai.** Con chrome-devtools sobre una pestaña de
claude.ai, guardando a `.fenix-docs.json` en la raíz del repo:

```js
async () => {
  const org = 'd1c8c86b-e73a-41aa-960f-cec33ddb08a3';
  const proj = '019f1f7a-042e-740b-a448-bad69dffd440';
  const docs = await (await fetch(`/api/organizations/${org}/projects/${proj}/docs`)).json();
  return docs.map(d => ({ file_name: d.file_name, content: d.content }));
}
```

**2. Ver el delta antes de tocar nada.**

```bash
cd apps/fenix/sync
python3 sincronizar.py ../../../.fenix-docs.json --dry-run
```

**3. Aplicarlo.**

```bash
python3 sincronizar.py ../../../.fenix-docs.json --corpus $(python3 -c "import json;print(json.load(open('estado.json'))['corpus'])")
```

**4. Verificar en la app, no en el log.** Preguntarle a fenix por un precio que
haya cambiado ese día y confirmar que responde el valor NUEVO. Un `200` del
upload sólo prueba que el archivo entró; que el modelo lo *recupere* es otra
cosa (ver el defecto de recall abierto en `../EXPERIMENTO.md`).

**5. Borrar el export.** `.fenix-docs.json` es temporal y está en `.gitignore`.

## Por qué hay un `estado.json`

Guarda el hash de cada documento sincronizado. Sin él, una sincronización diaria
degenera en una de dos cosas: re-subir los cuatro documentos completos cada día
(caro y ruidoso), o "revisar a ojo" qué cambió — que a la segunda semana falla en
silencio y nadie nota que la lista maestra del espejo lleva días vieja.

El `estado.json` **se commitea**: es el breadcrumb de qué se migró y cuándo. La
sesión que sincronice mañana no debe re-derivar nada.

## El slug corta la fecha del nombre, a propósito

El doc se llama `Lista de precios y reglas de venta (14-jul-2026 · actualizada)`
y esa fecha cambia cada vez que el equipo lo reescribe. Si el nombre del archivo
dependiera de ella, cada edición entraría como documento NUEVO y el corpus
acabaría con cinco listas maestras compitiendo entre sí. Por eso el slug se corta
en el primer paréntesis: `lista-de-precios-y-reglas-de-venta.md` sobrevive a las
reescrituras y siempre se reemplaza a sí mismo.

## Las conversaciones (`importar_conversaciones.py`)

Mismo ritual, otro script. Trae el HISTORIAL en vez de los documentos.

**1. Exportar las sesiones Cowork** desde claude.ai (el snippet completo está en
el encabezado del script; usa `/v1/code/sessions` + `/events`, que requieren los
headers `anthropic-version` y `x-organization-uuid` o devuelven 400).

**2. Delta y aplicar:**

```bash
python3 importar_conversaciones.py ../../../.fenix-convs.json --dry-run
python3 importar_conversaciones.py ../../../.fenix-convs.json
```

Primera corrida: **33 conversaciones, 323 mensajes** (las 35 menos dos sesiones
`__warming__` vacías). Idempotente por hash igual que los docs.

Dos decisiones dentro del script que conviene no deshacer:

- **Los mensajes se ordenan por timestamp.** El API de eventos no garantiza el
  orden de lectura, y un hilo desordenado se lee como una conversación distinta
  a la que ocurrió — el usuario preguntando después de que ya le respondieron.
- **Un fallo NO se registra en `estado.json`.** Si se registrara igual, la
  siguiente corrida daría esa conversación por importada y se perdería en
  silencio. Por eso el script termina con código 1 si hubo fallos.

**Esto exige que fenix use `RemoteConversationLibrary`** (el store del
servidor). Con el IndexedDB del navegador, el historial quedaría en la máquina
donde se corrió el script y nadie más lo vería.
