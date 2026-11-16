import Foundation

var failures = 0

func expect(_ condition: Bool, _ what: String) {
    if condition {
        print("  ok   \(what)")
    } else {
        failures += 1
        print("  FAIL \(what)")
    }
}

func canned(_ events: [StreamEvent]) -> ChatModel.Stream {
    { _, _, _, _, _, _ in
        AsyncThrowingStream { continuation in
            for event in events { continuation.yield(event) }
            continuation.finish()
        }
    }
}

func settle() async {
    for _ in 0..<50 { await Task.yield() }
    try? await Task.sleep(nanoseconds: 120_000_000)
}

/// Lo que depende de un poll se espera por su condición, no por un sueño fijo: un runner cargado no cumple los 120 ms.
@MainActor
func esperar(tope: UInt64 = 3_000_000_000, _ hecho: () -> Bool) async {
    let fin = DispatchTime.now().uptimeNanoseconds + tope
    while !hecho(), DispatchTime.now().uptimeNanoseconds < fin {
        try? await Task.sleep(nanoseconds: 10_000_000)
    }
}

/// Un archivo de `free-intelligence-core/contracts`, contado desde la carpeta de este arnés.
func rutaDeContrato(_ nombre: String) -> URL {
    URL(fileURLWithPath: #filePath).absoluteURL
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("packages/free-intelligence-core/contracts/\(nombre)")
}

@main
struct Harness {
    static func main() async {
        print("ChatModel — arnés de verificación (sin Xcode)")
        await autorSeCongelaPorMensaje()
        await elResultadoGanaALosDeltas()
        await cancelarNoDuplicaLaBurbuja()
        await elErrorNoInventaBurbuja()
        await elHistorialViajaSinElTurnoNuevo()
        derivacionesIgualesQueCore()
        await persisteAlCerrarElTurno()
        await elModeloViajaDeIdaYVuelta()
        elCorreoSaleDelIdToken()
        imagenAdjuntaComoLaWeb()
        await adjuntosTopanEnCuatro()
        await laImagenViajaYSePersiste()
        await reintentarConservaLaImagen()
        await restauraElHiloAlArrancar()
        await elIdDeConversacionEsElSessionID()
        await cambiarDeHiloNoMezclaMensajes()
        await laListaAgrupaComoElSidebarWeb()
        await laRedCaidaNoTeDesloguea()
        await elKeychainMudoAvisa()
        await cancelarNoPersisteRespuestaAMedias()
        await losGuardadosNoSePisan()
        await elElementoYElProyectoViajanEnElTurno()
        elJSONOmiteLoQueNoSeEligio()
        await elSaveNoBorraPinNiRename()
        await mutarUnChatEsLoadEditarSave()
        await elPlanYLosPasosSePintan()
        await nadaDesaparecEnSilencio()
        await elPlanNoSeArrastraEntreTurnos()
        elMarkdownPegadoSeRepara()
        await elTurnoVacioSeDeclara()
        await elTurnoBuenoNoOfreceReintento()
        await reintentarNoDuplicaLaBurbujaDelUsuario()
        await cancelarNoOfreceReintento()
        elParserLeeUnTurnoDeVerdad()
        elParserAguantaLoQueElServidorPuedeMandar()
        laSondaNoSeDisparaSola()
        await elArranqueEnFrioSeReintenta()
        await un401RefrescaElTokenYRepite()
        await dos401CierranLaSesion()
        await elTokenRechazadoNoSeReusa()
        elAutorSeLeeEnLasDosFormas()
        elAutorSeEscribeCanonico()
        guardarNoAmputaElRecordDeLaWeb()
        await cambiarDeChatNoArrastraElReintento()
        await elGuardBloqueaYSeVE()
        await cancelarElPlanNoEsCompletarlo()
        await elDesenlaceDelPlanLlega()
        await laEnmiendaViveEntreElAnuncioYElPlanNuevo()
        losFramesDelPlanYaNoSonBasura()
        resonanceElNucleoDeLaLlamada()
        await unaReaccionSolaEsRespuesta()
        await unTurnoDiferidoEsperaSinAcusarError()
        await laEsperaDiferidaNoEsEterna()
        await unaConexionCaidaNoRevierteElTurnoQueElServidorYaAbrio()
        await sinUnSoloFrameElTurnoSiSeRevierte()
        await pararAvisaAlServidorYVolverResincroniza()
        await elModeloAvisaCadaRespuestaQueEntra()
        await sinRedElHiloSeLeeDeLaCache()
        await unGuardadoQueNoLlegoSeVuelveASubir()
        elBorradorSobreviveYSeLimpia()
        await losVectoresDelTurnoSeCumplen()
        await losVectoresDeDerivacionesSeCumplen()
        await losVectoresDelHiloSeCumplen()
        await elAppendDelServidorNoSeDuplicaAlGuardar()
        print(failures == 0 ? "\nTODO VERDE" : "\n\(failures) FALLARON")
        exit(failures == 0 ? 0 : 1)
    }
}
