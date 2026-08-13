import Testing
@testable import og118

/// Prueba de viabilidad: ¿corre un test target en el Simulador SIN cuenta de
/// Apple? El target de UI (XCUITest) está bloqueado porque su runner necesita
/// bundle id propio y perfil de aprovisionamiento. Si los unit tests no lo
/// necesitan, el arnés casero puede volverse Swift Testing sin pagar ese atom.
@Test func elArnesPuedeVivirEnUnTestTarget() {
    var plan = TurnPlan()
    plan.declarar(["uno", "dos"])
    plan.cancelar()
    #expect(plan.pasos.allSatisfy { $0.estado == .cancelado })
    #expect(plan.desenlace == .cancelado)
}

@Test func elParserLeeUnFrameReal() {
    let datos = #"{"type":"text","text":"PONG"}"#.data(using: .utf8)!
    guard case .text(let t)? = StreamEvent.decode(datos) else {
        Issue.record("el frame no se decodificó"); return
    }
    #expect(t == "PONG")
}
