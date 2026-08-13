import XCTest

/// El turno de verdad, manejado por la máquina. Existe porque la única prueba
/// que quedaba del "no responde" era pedirle a Bernard que tecleara un mensaje
/// y me dijera qué pasó — usarlo de monkey clicker. Este test hace el turno
/// completo sobre la app instalada, reusando la sesión que ya vive en el
/// Keychain del teléfono.
final class TurnoRealTests: XCTestCase {

    func testLaAppContestaUnMensajeDeVerdad() throws {
        // Sin esto, el assert que falla no detiene el test: sigue tecleando
        // sobre una pantalla que no es la esperada y el reporte se llena de
        // fallos en cascada que esconden el primero, que es el único real.
        continueAfterFailure = false

        let app = XCUIApplication()
        app.launch()

        let composer = app.textFields["composer"]
        XCTAssertTrue(
            composer.waitForExistence(timeout: 20),
            "el composer no apareció (¿login?). En pantalla:\n" + loQueSeVe(app)
        )

        composer.tap()
        composer.typeText("Responde únicamente con la palabra PONG")

        let enviar = app.buttons["enviar"]
        XCTAssertTrue(enviar.waitForExistence(timeout: 5), "no hay botón de enviar")
        XCTAssertTrue(enviar.isEnabled, "el botón de enviar quedó deshabilitado con texto escrito")
        enviar.tap()

        // 120s porque el servidor escala a cero: el arranque en frío es parte
        // del turno real y contarlo como falla sería medir la infra, no la app.
        let respuesta = app.otherElements["respuesta"]
        let llego = respuesta.waitForExistence(timeout: 120)

        // Si no llegó, la bitácora del turno YA está en pantalla — llevarla al
        // fallo del test es lo que convierte un rojo mudo en un diagnóstico.
        if !llego {
            XCTFail("no llegó respuesta en 120s. En pantalla:\n" + loQueSeVe(app))
        }
    }

    /// La bitácora del turno se pinta en el hilo, así que volcar los textos de
    /// la pantalla convierte un rojo mudo en el diagnóstico completo.
    private func loQueSeVe(_ app: XCUIApplication) -> String {
        // Los textos NO bastan: la pantalla de login es casi toda botones, así
        // que un volcado de sólo staticTexts salía vacío — un diagnóstico que
        // no diagnostica.
        let textos = app.staticTexts.allElementsBoundByIndex.map { "texto: \($0.label)" }
        let botones = app.buttons.allElementsBoundByIndex.map { "botón: \($0.label)" }
        let campos = app.textFields.allElementsBoundByIndex.map { "campo: \($0.placeholderValue ?? $0.label)" }
        let todo = (textos + botones + campos).filter { !$0.hasSuffix(": ") }
        return todo.isEmpty ? "(nada legible en pantalla)" : todo.prefix(40).joined(separator: "\n")
    }
}
