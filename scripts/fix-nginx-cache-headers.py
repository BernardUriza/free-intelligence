#!/usr/bin/env python3
"""Fix Nginx cache headers to prevent stale HTML"""
import paramiko
import time

HOST = "104.131.175.65"
USER = "root"
PASSWORD = "FreeIntel2024DO!"

# Updated Nginx config with cache headers
NGINX_CONFIG = """# HTTP redirect to HTTPS
server {
    listen 80;
    server_name app.aurity.io;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name app.aurity.io;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/app.aurity.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.aurity.io/privkey.pem;

    # SSL configuration (HIPAA-compliant TLS)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Frontend (Next.js static export)
    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:7001/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Static assets (_next) - cache aggressively (immutable files with content hash)
    location /_next/static/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # HTML files - never cache (to avoid stale references)
    location ~* \\.html$ {
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        add_header Pragma "no-cache";
        add_header Expires "0";
        try_files $uri $uri/ /index.html;
    }

    # Frontend routes
    location / {
        # Don't cache the root HTML
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        try_files $uri $uri/ $uri.html /index.html;
    }
}
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, timeout=30)
    print("✅ Conectado\n")

    # Backup current config
    print("💾 Haciendo backup de configuración actual...")
    stdin, stdout, stderr = client.exec_command(
        "cp /etc/nginx/sites-enabled/aurity /etc/nginx/sites-enabled/aurity.backup.$(date +%Y%m%d_%H%M%S)"
    )
    stdout.channel.recv_exit_status()
    print("✅ Backup creado\n")

    # Write new config
    print("📝 Escribiendo nueva configuración...")
    stdin, stdout, stderr = client.exec_command(
        f"cat > /etc/nginx/sites-enabled/aurity << 'ENDOFCONFIG'\n{NGINX_CONFIG}\nENDOFCONFIG"
    )
    stdout.channel.recv_exit_status()
    print("✅ Configuración escrita\n")

    # Test config
    print("🧪 Probando configuración de Nginx...")
    stdin, stdout, stderr = client.exec_command("nginx -t")
    test_output = stderr.read().decode()
    print(test_output)

    if "successful" in test_output:
        print("✅ Configuración válida\n")

        # Reload Nginx
        print("🔄 Recargando Nginx...")
        stdin, stdout, stderr = client.exec_command("nginx -s reload")
        stdout.channel.recv_exit_status()
        time.sleep(1)
        print("✅ Nginx recargado\n")

        print("=" * 80)
        print("✅ CACHE HEADERS CONFIGURADOS")
        print("=" * 80)
        print("""
Cambios aplicados:
1. ✅ HTML files: NO cache (siempre fresh)
2. ✅ _next/static/*: Cache agresivo (archivos inmutables con hash)
3. ✅ Root location: NO cache (para evitar HTML stale)

Ahora prueba desde tu celular:
1. Clear cache/data del navegador
2. O abre en modo Incognito
3. Visita: https://app.aurity.io/

Los archivos JS/CSS deberían cargar correctamente.
        """)

    else:
        print("❌ Error en configuración de Nginx")
        print("Revirtiendo cambios...")
        stdin, stdout, stderr = client.exec_command(
            "mv /etc/nginx/sites-enabled/aurity.backup.* /etc/nginx/sites-enabled/aurity"
        )
        stdout.channel.recv_exit_status()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
