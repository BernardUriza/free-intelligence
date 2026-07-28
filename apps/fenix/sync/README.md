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

## Lo que este script NO migra todavía

**Las conversaciones.** El Project tiene 35 sesiones Cowork y 17 chats con
cotizaciones reales. No están aquí porque falta una decisión de arquitectura:
hoy fenix guarda sus conversaciones en el **IndexedDB del navegador**
(`useIndexedDBConversationLibrary`), así que importarlas al servidor no las haría
aparecer en la UI. El camino canónico es mover fenix a
`RemoteConversationLibrary` — el primitivo ya existe en fi-glass y og118 lo usa
cuando hay sesión iniciada — para que el historial sea del negocio y no del
navegador de quien lo abrió. Ver `../EXPERIMENTO.md`.
