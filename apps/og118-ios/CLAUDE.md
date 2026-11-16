# og118-ios — el cliente nativo de iPhone

SwiftUI, sin dependencias, contra el mismo servidor que `app.og118.ai`. El estado vivo y cada incidente están
en `.claude/backlog/og118-ios-tracer.md`; la anatomía, en `README.md`.

## Reglas de esta carpeta

- **Es la segunda superficie del mismo contrato.** fi-glass no cruza a Swift: lo que la web resuelve en
  `apps/og118/web/lib/useOg118Agent.ts` y en `fi-glass/src/agent` se porta aquí a mano. Antes de inventar un
  comportamiento, lee cómo lo hace la web. Los tipos del cable, el record, el tema y los textos son generados
  (`Sources/Services/Generated`, `Sources/Views/Generated`): se regeneran desde core, nunca se editan.
- **Toda petición sale por `Services/Transporte.swift`.** Ningún `URLSession.shared.data` suelto con su propio
  manejo de 401.
- **El equipo de firma vive sólo en `Config.xcconfig`.** Nunca en `project.yml`.
- **Un cambio se prueba en tres niveles**: el arnés de macOS (`Tests/Harness/*.swift`, corre en CI), los
  unit tests en simulador (`xcodebuild test -only-testing:OG118UnitTests`, corre en CI) y el teléfono. Lo que
  no se probó en el teléfono se escribe como «sin verificar en el teléfono», no como hecho.
- **`xcrun` necesita `DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer`** en esta Mac:
  `xcode-select` apunta a las CommandLineTools.
- **Nunca se repite `devicectl device process launch`** sobre una app sin confianza: cada intento le salta una
  alerta en el teléfono.

## Probar

```bash
cd apps/og118-ios
SDK=$(xcrun --show-sdk-path --sdk macosx)
swiftc -DDEBUG -sdk "$SDK" -target arm64-apple-macos14.0 -o /tmp/og118-harness \
  Sources/Models/*.swift Sources/Services/*.swift Sources/Services/Generated/*.swift \
  Sources/Services/Voice/*.swift Tests/Harness/*.swift && /tmp/og118-harness

export DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer
xcodegen generate
xcodebuild -project OG118.xcodeproj -scheme OG118 \
  -destination "platform=iOS Simulator,id=<udid>" -only-testing:OG118UnitTests test
```
