# Mobile Viewport UX — el contenido manda (CONV-MOBILE-RECLAIM-1)

Registrada 2026-07-13. En móvil, la conversación es la prioridad visual; el
chrome de interfaz (header, composer, banners) es sirviente. Estas reglas
gobiernan fi-glass (anatomía) y sus consumers (og118, futuros shells).

## Presupuestos duros (breakpoint móvil ≤768px)

- **Chrome no-contenido < 18% del viewport** (medido: header + composer región +
  banners persistentes, en idle). Tras el refactor: ~7.5% @390×844.
- **Header interno**: hoy NO existe (el hamburger es un overlay flotante 44×44 —
  correcto). Si algún día se agrega uno: 48–56px máximo.
- **Composer idle**: caja ≤64px; región completa (con paddings + safe-area)
  ≤ ~100px. Crece solo con contenido (multilínea hasta `maxRows`) o con el rail
  expandido.
- **Gutters de conversación**: 12px por lado (`--fi-transcript-pad`). El
  `contentInset` del surface es `100%` en móvil — el inset de 16px extra fue
  eliminado; no lo reintroduzcas encima de los gutters.
- **Mensajes**: padding ~10px 14px (`max-md:` en `messages/styles.ts`), radius
  14px (glass-chat móvil), body 16px / line-height 1.5 en móvil (14px desktop),
  SIN indent de avatar en móvil (`pl-8` es `md:`-only).
- **Touch targets ≥44×44 siempre** (`fi-touch-target`); nunca se reduce un
  target para ganar espacio — se recoloca (wrap, disclosure).

## Acciones primarias vs secundarias

- **Send es la única acción primaria siempre visible** del composer. El mic
  (dictado) la acompaña por ser producto-de-voz.
- **Todo lo demás del composer** (persona/modelo, llamada, adjuntar) vive en el
  rail `footer-start`, que en containers ≤420px se colapsa tras el toggle de
  disclosure de `ComposerFrame` (`.fi-composer-rail-toggle`, `aria-expanded`).
- **Acciones por-mensaje** (copiar, escuchar): en pointer fino se revelan por
  hover/focus con espacio reservado (sin layout shift); en touch están ocultas
  salvo (a) el último mensaje del hilo, (b) tap en el mensaje
  (`data-fi-actions-open`), vía `messageActionsStyle` de fi-glass. No agregues
  filas de acciones siempre-visibles.

## Breakpoints canónicos (no inventes nuevos)

- `768px` — media query móvil global (shell drawer, tokens de spacing,
  variantes `max-md:`).
- `@container fi-composer (max-width: 420px)` — composer compacto (fi-glass:
  frame en fila + disclosure; og118: labels/paddings).
- `@container fi-composer (max-width: 340px)` — extremo 320px-class (badge
  atómico cede).
- Safe-areas: `env(safe-area-inset-*)` obligatorio en los bordes fijos
  (composer bottom, drawer top, sidebar footer).

## Tokens de spacing del surface

Definidos en `densityStyle.ts` (scope `.fi-agent-workspace`), consumidos por las
regiones con su literal desktop como fallback:
`--fi-transcript-pad`, `--fi-transcript-gap`, `--fi-composer-bar-pt/-px/-pb`.
Un consumer re-tunea seteando las vars; NO edites literales inline en las
regiones ni esparzas magic numbers nuevos.

## Protocolo de verificación — un claim "cabe en móvil" se MIDE en el render real

Toda PR que afirme "cabe en móvil", "se ve bien en móvil" o cualquier claim de
layout responsive DEBE verificarse **midiendo el render real** a ancho de columna
de teléfono ANTES de aprobar o mergear. Un test SSR que verifica que el markup
contiene los elementos (`toContain('Transcribir')`) es necesario pero **NO
suficiente**: prueba que el DOM tiene el elemento, no que el layout lo deja
visible. Aprobar sobre markup verde sin medir el render es el fake-green de Art. 2
(ver también [[verify-before-assuming]] Rule 10/12).

### El ancho canónico: 374px

La columna de un teléfono a 390px de viewport menos los gutters del composer
(`px-2` = 8px por lado) = **374px de contenido**. Ésa es la columna que se mide,
no los 390 crudos. Para el caso 320px-class, repetir a 304px.

### La medición mínima (Chrome real, no jsdom)

jsdom no hace layout — la medición va en Chrome (chrome-devtools MCP). El window
de Chrome tiene ancho mínimo (~500px), así que se fuerza un contenedor de 374px y
se mide dentro de él con `getBoundingClientRect`:

```js
() => {
  const wrap = document.querySelector('[data-verify]');
  wrap.style.width = '374px'; wrap.style.boxSizing = 'border-box';
  void wrap.offsetWidth;
  const primary = wrap.querySelector('.<accion-primaria>');
  const row = wrap.querySelector('.<fila>');
  return {
    primaryFitsInColumn: primary.getBoundingClientRect().right <= wrap.getBoundingClientRect().right + 0.5,
    rowScrollOverflowPx: row.scrollWidth - row.clientWidth, // debe ser 0
  };
}
```

Aprobación requiere: `primaryFitsInColumn === true` **Y** `rowScrollOverflowPx === 0`,
más un screenshot como recibo visual (Art. 2). El harness es una ruta efímera bajo
`app/` (sin prefijo `_` — ése es carpeta privada, 404) que rinde el componente REAL
con Tailwind real; se borra tras medir, nunca se comitea.

### Por qué existe este protocolo

PR #373 shippeó un commit *"mobile-first keeps Transcribir visible"* cuyos tests
sólo verificaban que el string `"Transcribir"` existía en el markup SSR — verde
pero ciego al layout. La afirmación de que el botón primario cabía en pantalla
sólo se pudo confirmar midiendo el flex real a 374px (`Transcribir` right-edge
dentro de la columna, cero overflow). Fue verdadera, pero llegó sin verificar; el
protocolo cierra ese hueco.

## Por qué existe

El PWA de og118 @390×844 gastaba 18.6% del viewport en composer (157px), 32px
de indent muerto por mensaje y acciones permanentes en touch — "un layout de
desktop comprimido a móvil". El refactor (branch
`bernarduriza/mobile-viewport-reclaim`) lo bajó a 63px (7.5%) con texto de
mensaje a 366px de ancho en 390. Archivos: fi-glass `messages/styles.ts`,
`MessageBubble` + `messageActionsStyle`, `ComposerFrame`, regiones
transcript/composer, `densityStyle`, `useSurfaceLayout`,
`AutoResizeTextarea` (textarea vacío = 1 fila SIEMPRE, el placeholder no
infla); og118 `globals.css`.
