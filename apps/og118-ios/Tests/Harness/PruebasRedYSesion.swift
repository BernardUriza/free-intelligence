import Foundation

// MARK: - El servidor dormido

func elArranqueEnFrioSeReintenta() async {
    print("la primera petición despierta al servidor; la segunda es la buena")
    var intentos = 0
    let valor = try? await ArranqueEnFrio.conReintento { esReintento -> String in
        intentos += 1
        if !esReintento { throw URLError(.timedOut) }
        return "ok"
    }
    expect(intentos == 2, "hubo un reintento (hubo \(intentos))")
    expect(valor == "ok", "y el segundo intento entrega el dato")

    // Un fallo que no es de red no se reintenta: repetirlo daría el mismo
    // error y sólo retrasaría el mensaje al humano.
    var intentosAuth = 0
    let fallo = try? await ArranqueEnFrio.conReintento { _ -> String in
        intentosAuth += 1
        throw Og118Error.unauthorized
    }
    expect(intentosAuth == 1, "un 401 NO se reintenta (hubo \(intentosAuth))")
    expect(fallo == nil, "y el error sube")

    var intentosBuenos = 0
    let directo = try? await ArranqueEnFrio.conReintento { _ -> String in
        intentosBuenos += 1
        return "rápido"
    }
    expect(intentosBuenos == 1, "si responde a la primera no se repite")
    expect(directo == "rápido", "y devuelve lo suyo")

    expect(ArranqueEnFrio.esDeRed(URLError(.cannotConnectToHost)), "no conectar es de red")
    expect(ArranqueEnFrio.esDeRed(Og118Error.badStatus(500)) == false, "un 500 no es de red")
}

// MARK: - Un 401 no es el fin de la sesión

func respuesta(_ codigo: Int) -> (Data, URLResponse) {
    (Data("{}".utf8), HTTPURLResponse(url: Config.apiBase, statusCode: codigo, httpVersion: nil, headerFields: nil)!)
}

func un401RefrescaElTokenYRepite() async {
    print("un 401 con el token cacheado refresca una vez y repite la petición")
    var pedidos: [String?] = []
    var enviados: [String] = []
    var cierres = 0
    let transporte = Transporte(
        token: { rechazado in
            pedidos.append(rechazado)
            return rechazado == nil ? "viejo" : "nuevo"
        },
        sesionRechazada: { cierres += 1 },
        datos: { request in
            let credencial = request.value(forHTTPHeaderField: "Authorization") ?? ""
            enviados.append(credencial)
            return respuesta(credencial == "Bearer viejo" ? 401 : 200)
        }
    )
    let resultado = try? await transporte.enviar(URLRequest(url: Config.apiBase))
    expect(resultado?.1.statusCode == 200, "la segunda vuelta entrega el 200")
    expect(enviados == ["Bearer viejo", "Bearer nuevo"], "se mandó primero el viejo y luego el nuevo (\(enviados))")
    expect(pedidos.count == 2 && pedidos[0] == nil && pedidos[1] == "viejo", "el refresco nombra el token rechazado")
    expect(cierres == 0, "y la sesión sigue abierta")
}

func dos401CierranLaSesion() async {
    print("si el servidor rechaza también el token nuevo, la sesión se cierra")
    var vueltas = 0
    var cierres = 0
    let transporte = Transporte(
        token: { _ in "cualquiera" },
        sesionRechazada: { cierres += 1 },
        datos: { _ in
            vueltas += 1
            return respuesta(401)
        }
    )
    var error: Error?
    do { _ = try await transporte.enviar(URLRequest(url: Config.apiBase)) } catch let fallo { error = fallo }
    var esNoAutorizado = false
    if case .unauthorized? = error as? Og118Error { esNoAutorizado = true }
    expect(vueltas == 2, "dos intentos, no un ciclo (hubo \(vueltas))")
    expect(cierres == 1, "se avisa UNA vez que la sesión murió")
    expect(esNoAutorizado, "y el error que sube es el de sesión")

    var sinCredencial = 0
    let vacio = Transporte(token: { _ in "" }, sesionRechazada: {}, datos: { _ in
        sinCredencial += 1
        return respuesta(200)
    })
    _ = try? await vacio.enviar(URLRequest(url: Config.apiBase))
    expect(sinCredencial == 0, "un token vacío nunca sale sin credencial")
}

@MainActor
func elTokenRechazadoNoSeReusa() async {
    print("Auth cambia un access token rechazado aunque el reloj diga que sigue vivo")
    var intercambios = 0
    let auth = Auth(deps: AuthDependencies(
        exchange: { _ in
            intercambios += 1
            return TokenResponse(accessToken: "at-\(intercambios)", refreshToken: "rt", expiresIn: 3600)
        },
        keychainRead: { "previo" },
        keychainSave: { _ in true },
        keychainDelete: {}
    ))
    let primero = try? await auth.token()
    let repetido = try? await auth.token()
    expect(primero == "at-1" && repetido == "at-1" && intercambios == 1, "vigente y sin rechazo: se reusa")
    let nuevo = try? await auth.token(rechazado: "at-1")
    expect(nuevo == "at-2", "rechazado: se refresca (llegó \(nuevo ?? "nada"))")
    let tardio = try? await auth.token(rechazado: "at-1")
    expect(tardio == "at-2" && intercambios == 2, "otro caller con el mismo rechazo no quema un segundo refresh")

    auth.cerrarPorRechazo()
    expect(!auth.isSignedIn && auth.avisoDeSalida != nil, "cerrar por rechazo deja dicho por qué")
    auth.signOut()
    expect(auth.avisoDeSalida == nil, "salir a mano no deja aviso")
}
