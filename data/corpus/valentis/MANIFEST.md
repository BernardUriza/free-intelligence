# Corpus — valentis (ética del cuidado)

Corpus abierto el **2026-09-16** (issue #61, punto B). Hasta ese día Valentis era
la única de las seis personas **sin corpus**: el registry decía "fase 2, no entra
hoy". La decisión de abrirlo es de Álex.

Artículo open access bajado como **full-text XML** vía Europe PMC REST
(`/webservices/rest/<PMCID>/fullTextXML`), el mismo camino que ya usaba
`frugivoro` porque el endpoint PDF de NCBI bloquea clientes no-navegador. El XML
es texto real (JATS) y el ingestor lo soporta. Los archivos están gitignored;
este MANIFEST sí se versiona.

| Título | Autor | Año | Origen | Licencia / estatus | Filename local |
|---|---|---|---|---|---|
| Engaging otherness: care ethics radical perspectives on empathy — **por qué:** es la ética del cuidado discutiendo su propia herramienta; distingue tres formas de empatía y señala que la empatía común falla justo con quien se percibe como "otro" | Jolanda van Dijke, Inge van Nistelrooij, Pien Bos, Joachim Duyndam | 2023 | https://pmc.ncbi.nlm.nih.gov/articles/PMC10425473/ (Europe PMC fullTextXML) · DOI 10.1007/s11019-023-10152-0 | Open access — **CC BY 4.0**, verificada dentro del propio XML | vandijke_2023_care_ethics_empathy.xml |

## La regla que hace distinto a este corpus

En las demás personas, citar la procedencia es lo correcto siempre. **Aquí no.**
El header de Valentis le ordena decidir primero si citar viene al caso: a alguien
que está mal no se le cita literatura. El corpus existe para que ELLA entienda
mejor lo que está haciendo, no para mostrárselo a quien escribe. Eso sale
directo de su ADN — *"acompañas; no tratas"*, y la referencia sin tacto que *"se
siente como una puerta cerrándose"*.

## Notas de verificación

- La licencia se leyó **dentro del XML descargado** (`creativecommons.org/licenses/by/4.0/`),
  no en la página del editor.
- Dry-run del 2026-09-16: 81,968 chars → 46 chunks, cero dropped, cero no_text.

## Pendientes de copyright (átomo de Bernard — NO descargados)

- Nel Noddings — *Caring: A Relational Approach to Ethics and Moral Education*
  (copyright). Es la obra fundacional de la ética del cuidado; el artículo de van
  Dijke la discute.
- Carol Gilligan — *In a Different Voice* (copyright).
