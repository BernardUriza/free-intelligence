# Corpus — frugivoro (gastronomía vegana / nutrición)

Un clásico vegetariano de dominio público + reviews open access (CC BY) de PMC.
Los binarios están gitignored; este MANIFEST sí se versiona.

| Título | Autor | Año | Origen | Licencia / estatus | Filename local |
|---|---|---|---|---|---|
| The Ethics of Diet: A Catena of Authorities Deprecatory of the Practice of Flesh Eating | Howard Williams | 1883 | https://www.gutenberg.org/ebooks/55785 | Dominio público (Project Gutenberg) | williams_ethics_of_diet.txt |
| Plant-based diets for human health with implications for cardiometabolic health | (Frontiers in Nutrition) | 2025 | https://pmc.ncbi.nlm.nih.gov/articles/PMC13163209/ (Europe PMC fullTextXML) | Open access — CC BY | plant_based_diets_cardiometabolic_review_PMC13163209.xml |
| Plant-Based Diet and Pregnancy-Related Disorders: A Narrative Review | (narrative review) | 2025 | https://pmc.ncbi.nlm.nih.gov/articles/PMC13086723/ (Europe PMC fullTextXML) | Open access — CC BY | plant_based_diet_pregnancy_review_PMC13086723.xml |
| Speciesism in everyday language — **por qué:** no debate si el especismo está mal: lo mide en el lenguaje cotidiano | Stefan Leach, Andrew P. Kitchin, Robbie M. Sutton, Kristof Dhont | 2023 | https://pmc.ncbi.nlm.nih.gov/articles/PMC10086848/ (Europe PMC fullTextXML) · DOI 10.1111/bjso.12561 | Open access — **CC BY 4.0**, verificada dentro del XML | leach_2023_speciesism_in_everyday_language.xml |
| Sabores Tapatíos: platillos tradicionales para salvar a los animales — **por qué:** 12 recetas jaliscienses veganas (torta ahogada, birria, pozole, tejuino…), la cocina local que Frugi no tenía | Love Veg / Igualdad Animal México | 2026 | https://loveveg.mx/app/uploads/2026/09/sabores-tapatios-para-salvar-animales.pdf | Recetario gratuito publicado por la ONG; sin licencia explícita (uso interno de RAG, no se redistribuye) | loveveg_sabores_tapatios_2026.md |

## Notas
- Williams "The Ethics of Diet" hallado en Gutenberg #55785 (verificado por título/autor).
- Las 2 reviews de PMC se bajaron como **full-text XML** vía Europe PMC REST
  (`/webservices/rest/<PMCID>/fullTextXML`) porque el endpoint PDF de NCBI bloquea
  clientes no-navegador. El XML es texto real (JATS), ingesta-friendly para RAG.
  Ambas confirmadas `isOpenAccess:Y`, `license: cc by`.

- Sabores Tapatíos (19-nov-2026): el PDF trae las letras como trazos vectoriales (pdftotext da 29 caracteres para 29 páginas), así que la fuente ingerida es una transcripción `.md` hecha leyendo cada página (OCR tesseract + revisión visual de las páginas de ingredientes sobre foto).

## Pendientes de copyright
- (ninguno solicitado — los recetarios veganos comerciales quedarían como átomo de Bernard si se desean)
