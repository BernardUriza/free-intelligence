# Setup de la máquina

Lo que de verdad hace falta. Es mucho menos de lo que parece, y lo que parece
obligatorio casi te cuesta la sesión 1 completa.

## Primero verifica, no instales

En la sesión 1 la máquina ya traía **todo** menos Claude Code:

```powershell
git --version; node --version; npm --version; python --version
```
```
git version 2.54.0.windows.1
v24.15.0
11.12.1
Python 3.14.5
```

Y de pilón `gh` 2.95 ya instalado **y autenticado**, lo que dejó aceptar el
invite del repo desde su propia sesión sin pelear con la UI de GitHub.

La persona dijo *"no sé si tengo todo eso instalado, déjame checar en GitHub"* —
o sea que ni ella lo sabía, y confundía GitHub (la página) con los programas de
su compu. **Ese chequeo es del operador, no suyo.** Dos comandos desde tu lado
contra media hora de que ella busque en el lugar equivocado.

## Lo único que se instala

```powershell
npm install -g @anthropic-ai/claude-code     # ~46 s
claude --version                             # verificar que quedó en el PATH
```

Después, `claude` dentro del repo → login. **El login es el átomo humano**: la
cuenta la decide y la teclea la persona dueña de la credencial, nunca el agente.

## El entorno de Python: NO uses el pesado

Éste es el hallazgo que salvó la sesión.

El repo es conda-managed y `environment.yml` arrastra `sentence-transformers` →
torch: **el env de conda pesa 1.4 GB**. En una máquina nueva y una conexión
doméstica, eso es una hora larga mirando una barra de progreso, y la sesión se
acaba sin escribir una línea.

**No hace falta.** El test que necesita el issue solo importa `shared.personas` y
la biblioteca estándar. Con Python 3.14 + pytest y nada más:

```powershell
python -m venv .venv-alex
.venv-alex/Scripts/python.exe -m pip install pytest
.venv-alex/Scripts/python.exe -m pytest tests/shared/test_registry_insult.py -q
```

Medido: **27 MB** de entorno, `11 passed in 0.02s`.

> **Antes de decidir el entorno, prueba el test que la persona va a correr.**
> No lo deduzcas del `environment.yml` del repo — corre el archivo concreto en un
> venv mínimo y mira si pasa. Es un minuto de trabajo que puede ahorrar una hora
> de descarga.

La suite completa sí necesita el entorno grande — **y para eso está el CI**, que
la corre en el PR. La persona no tiene que cargarla en su máquina.

**Ojo con la versión de Python**: el mínimo no es "cualquier Python". Con el
Python 3.9 del sistema el `conftest.py` truena al importar (`NameError` en una
anotación). Es la versión, no las dependencias.

## El gestor de paquetes que olvidaste sigue votando

Hallazgo del **2026-09-03**, actualizando el entorno a `fi-core 0.27.0`.

El síntoma es de los que hacen perder horas porque **todo dice que está bien**:

```
mamba env update -f environment.yml   ->  "All requested packages already installed"
python -c "import fi_core; print(fi_core.__version__)"  ->  0.26.1
```

`environment.yml` pinea `fi-core=0.27.0`, mamba jura que ya está, y el runtime
carga la vieja. Y como el código nuevo pide la API de 0.27.0, lo que truena
truena por un motivo que no aparece en ningún lado.

**La causa:** `fi-core` y `fi-runner` estaban instalados por **pip encima de
conda**. Dos gestores creyendo que mandan sobre el mismo env, y el runtime
cargando el que perdió.

### El comando que lo destapa

```powershell
conda list -n <env> | Select-String "<paquete>"
```

Si la columna de canal dice `pypi_0` en vez del canal de conda, ahí está:

```
fi-core     0.26.1     pypi_0     pypi        # <- lo puso pip
fi-core     0.27.0     py_0       <canal>     # <- lo puso conda
```

El equivalente de Insult para un `.venv` es `pip freeze | grep <paquete>`. Es el
mismo pecado con otro traje.

### El comando que lo cura

```powershell
<env>/python.exe -m pip uninstall -y <paquete-1> <paquete-2>
mamba install -n <env> -c <canal> "<paquete-1>=<version>" --force-reinstall -y
```

**El `--force-reinstall` no es opcional.** Al desinstalar con pip se borran los
archivos, pero los metadatos de conda quedan intactos: conda sigue reportando el
paquete como instalado mientras Python contesta `ModuleNotFoundError`. Sin
forzar, `mamba install` vuelve a decir "already installed" y no repara nada.

> **La regla, más allá de este caso:** cualquier gestor de paquetes olvidado
> sigue votando en el runtime. Antes de perseguir un fantasma, pregunta **quién
> instaló** la versión que se está cargando, no sólo **cuál** es.

## Clonar

```powershell
cd $HOME; git clone https://github.com/<owner>/<repo>.git
```

Si ya tiene GitHub configurado en esa máquina, el Credential Manager resuelve el
acceso al repo privado sin pedir nada. En la sesión 1 el clone fueron **3.6 MiB**.

### Activa los hooks — un comando, y hay que correrlo

```bash
git config core.hooksPath .githooks
```

Git **no** activa hooks al clonar, ni siquiera los que están en el repo. Sin este
comando, la persona commitea sin ninguna red: sin gate de ruff (el mismo que CI
va a reprobarle), sin la revisión de `environment.yml`, y sin el candado de
versión que exige que `pyproject.toml` y `VERSION_TAG` se muevan **juntos y
coincidiendo**.

**Por qué está en la checklist y no como nota al pie (2026-08-12):** el hook
vivía en `.git/hooks/`, que no se versiona — o sea que protegía exactamente una
máquina, la de Bernard, mientras quien más lo necesita es quien está aprendiendo.
Además listaba `personas/insult/__init__.py`, borrado en la purga de julio, y
salía en verde con **medio** bump: decía "bump all 3" pero pasaba con el primero
que encontrara. Bumpear sólo `pyproject.toml` desplegaba un bot cuyo tag de
versión mentía — y ese tag es justo con lo que se verifica que un deploy aterrizó
(`.claude/rules/testing.md`). Verificar el deploy se volvía un volado.

## AnyDesk

- La licencia gratis permite **una sola sesión**. Si tienes otra abierta (por
  ejemplo a tu propia PC remota), bloquea la nueva con *"Session limit reached"*.
  Terminarla solo cierra el visor; la máquina remota sigue viva.
- **Pantalla completa (`⌘F` o `Display → Full-screen`) antes de hacer clics.**
  Con la ventana escalada, las coordenadas se descuadran y terminas clicando en
  el navegador de la otra persona.
- Para pasar a solo lectura: `Permissions → Control remote device` **OFF**.
  Verificable — la palomita del menú desaparece. **Nunca** uses *"Block remote
  input"*: eso bloquea el teclado de la persona, que es lo contrario.

## Checklist de arranque

- [ ] Verificados git / node / npm / python **antes** de instalar nada
- [ ] Claude Code instalado y en el PATH
- [ ] Cuenta decidida y login hecho (por la persona)
- [ ] Repo clonado
- [ ] **`git config core.hooksPath .githooks` corrido** (sin esto no hay hooks)
- [ ] Invite de colaborador aceptado
- [ ] Entorno mínimo de Python + pytest (**no** el env pesado)
- [ ] Verificado que **un solo gestor** instaló los paquetes del proyecto
- [ ] **Tests en verde en su máquina, antes de tocar código**
- [ ] Control remoto devuelto (solo lectura) y avisado por Discord
