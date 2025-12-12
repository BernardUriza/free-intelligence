#!/usr/bin/env python3
"""Verify Auth0 audience configuration"""

import json

import paramiko

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)

    # Get full response
    stdin, stdout, stderr = client.exec_command("curl -s http://localhost:7001/api/auth/config")
    response = stdout.read().decode()

    print("📋 Respuesta completa:")
    print("=" * 80)

    try:
        config = json.loads(response)
        print(json.dumps(config, indent=2))

        print("\n" + "=" * 80)
        print("🎯 Audience actual:", config.get("audience"))

        if config.get("audience") == "https://app.aurity.io":
            print("✅ CORRECTO - Sin subdominio 'api.'")
        elif config.get("audience") == "https://api.app.aurity.io":
            print("❌ INCORRECTO - Todavía tiene subdominio 'api.'")
        else:
            print(f"⚠️  INESPERADO - Valor: {config.get('audience')}")

    except json.JSONDecodeError:
        print(response)
        print("\n❌ Respuesta no es JSON válido")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    client.close()
