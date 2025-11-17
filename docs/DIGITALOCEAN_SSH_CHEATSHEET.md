# 🔐 DigitalOcean SSH Cheatsheet - Free Intelligence

## 📋 Configuración del Servidor

```bash
SERVER_IP=104.131.175.65
SSH_KEY=~/.ssh/id_ed25519_do
USERNAME=root
```

---

## 🚀 Comandos SSH Esenciales

### Conectar al Servidor

```bash
# Con SSH key (recomendado)
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65

# Con password (backup)
ssh root@104.131.175.65
# Password: FreeIntel2024DO!

# Alias útil (agregar a ~/.bashrc)
alias fi-ssh='ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65'
```

### Deploy Rápido (One-liner)

```bash
# Pull + Restart backend
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 \
  "cd /opt/free-intelligence && git pull && systemctl restart fi-backend"

# Con alias
fi-ssh "cd /opt/free-intelligence && git pull && systemctl restart fi-backend"
```

---

## 🐳 Docker Commands via SSH

### Ver Containers

```bash
# Listar containers corriendo
ssh -i $SSH_KEY root@$SERVER_IP "docker ps"

# Ver TODOS los containers
ssh -i $SSH_KEY root@$SERVER_IP "docker ps -a"

# Ver imágenes
ssh -i $SSH_KEY root@$SERVER_IP "docker images"
```

### Logs y Debugging

```bash
# Ver últimas 50 líneas de logs
ssh -i $SSH_KEY root@$SERVER_IP "docker logs fi-backend --tail 50"

# Follow logs (real-time)
ssh -i $SSH_KEY root@$SERVER_IP "docker logs fi-backend -f"

# Ver uso de recursos
ssh -i $SSH_KEY root@$SERVER_IP "docker stats --no-stream"

# Inspeccionar container
ssh -i $SSH_KEY root@$SERVER_IP "docker inspect fi-backend"
```

### Restart/Stop/Start

```bash
# Restart container
ssh -i $SSH_KEY root@$SERVER_IP "docker restart fi-backend"

# Stop container
ssh -i $SSH_KEY root@$SERVER_IP "docker stop fi-backend"

# Start container
ssh -i $SSH_KEY root@$SERVER_IP "docker start fi-backend"

# Stop y eliminar
ssh -i $SSH_KEY root@$SERVER_IP "docker stop fi-backend && docker rm fi-backend"
```

### Build y Deploy

```bash
# Build nueva imagen
ssh -i $SSH_KEY root@$SERVER_IP \
  "cd /opt/free-intelligence && docker build -t fi-backend ."

# Run nuevo container
ssh -i $SSH_KEY root@$SERVER_IP \
  "docker run -d --name fi-backend -p 7001:7001 --env-file .env fi-backend:latest"

# Deploy completo (stop → rm → build → run)
ssh -i $SSH_KEY root@$SERVER_IP << 'ENDSSH'
cd /opt/free-intelligence
docker stop fi-backend || true
docker rm fi-backend || true
git pull
docker build -t fi-backend .
docker run -d --name fi-backend -p 7001:7001 --restart unless-stopped fi-backend:latest
ENDSSH
```

---

## 📁 File Transfer (SCP)

### Upload Files

```bash
# Subir archivo al servidor
scp -i ~/.ssh/id_ed25519_do \
  local-file.txt \
  root@104.131.175.65:/opt/free-intelligence/

# Subir directorio completo
scp -i ~/.ssh/id_ed25519_do -r \
  local-directory/ \
  root@104.131.175.65:/opt/free-intelligence/
```

### Download Files

```bash
# Descargar archivo del servidor
scp -i ~/.ssh/id_ed25519_do \
  root@104.131.175.65:/opt/free-intelligence/storage/corpus.h5 \
  ./

# Descargar logs
scp -i ~/.ssh/id_ed25519_do \
  root@104.131.175.65:/var/log/fi-backend.log \
  ./logs/
```

---

## 🐍 Python Paramiko Automation

### Script de Deploy Automatizado

```python
#!/usr/bin/env python3
"""
DigitalOcean Deployment Script using Paramiko
Usage: python3 deploy_paramiko.py
"""

import paramiko
import sys

def deploy_to_do():
    """Deploy Free Intelligence backend to DigitalOcean"""

    # Connection config
    HOST = '104.131.175.65'
    USER = 'root'
    PASSWORD = 'FreeIntel2024DO!'

    # Connect
    print(f"🔐 Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False)
        print("✅ Connected!")

        # Deploy commands
        commands = [
            "cd /opt/free-intelligence",
            "git pull",
            "docker stop fi-backend || true",
            "docker rm fi-backend || true",
            "docker build -t fi-backend .",
            "docker run -d --name fi-backend -p 7001:7001 --restart unless-stopped fi-backend:latest",
            "sleep 3",
            "docker ps",
            "curl -s http://localhost:7001/api/health || echo 'Backend starting...'"
        ]

        print("\n🚀 Deploying...")
        for cmd in commands:
            print(f"\n▶️  {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)

            # Print output
            output = stdout.read().decode()
            error = stderr.read().decode()

            if output:
                print(output)
            if error and "WARNING" not in error:
                print(f"⚠️  {error}")

        print("\n✅ Deployment complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    deploy_to_do()
```

### Check Server Status

```python
#!/usr/bin/env python3
"""Quick server status check"""

import paramiko

HOST = '104.131.175.65'
USER = 'root'
PASSWORD = 'FreeIntel2024DO!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False)

# Check Docker containers
stdin, stdout, stderr = client.exec_command('docker ps')
print("🐳 Docker Containers:")
print(stdout.read().decode())

# Check backend health
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:7001/api/health')
print("\n💚 Backend Health:")
print(stdout.read().decode())

# Check disk space
stdin, stdout, stderr = client.exec_command('df -h | grep -E "Filesystem|/$"')
print("\n💾 Disk Usage:")
print(stdout.read().decode())

client.close()
```

---

## 🔧 Troubleshooting

### Backend no responde

```bash
# 1. Verificar que el container está corriendo
ssh -i $SSH_KEY root@$SERVER_IP "docker ps | grep fi-backend"

# 2. Ver logs recientes
ssh -i $SSH_KEY root@$SERVER_IP "docker logs fi-backend --tail 100"

# 3. Verificar puerto
ssh -i $SSH_KEY root@$SERVER_IP "netstat -tulpn | grep 7001"

# 4. Restart container
ssh -i $SSH_KEY root@$SERVER_IP "docker restart fi-backend"
```

### Container no arranca

```bash
# Ver logs completos
ssh -i $SSH_KEY root@$SERVER_IP "docker logs fi-backend"

# Verificar imagen existe
ssh -i $SSH_KEY root@$SERVER_IP "docker images | grep fi-backend"

# Rebuild desde cero
ssh -i $SSH_KEY root@$SERVER_IP << 'ENDSSH'
cd /opt/free-intelligence
docker build --no-cache -t fi-backend .
docker run -d --name fi-backend -p 7001:7001 fi-backend:latest
ENDSSH
```

### Git pull falla

```bash
# Reset repo a estado limpio
ssh -i $SSH_KEY root@$SERVER_IP << 'ENDSSH'
cd /opt/free-intelligence
git reset --hard origin/main
git clean -fd
git pull
ENDSSH
```

---

## 📊 Monitoring

### Quick Health Check Script

```bash
#!/bin/bash
# save as: check-server.sh

SSH_KEY=~/.ssh/id_ed25519_do
SERVER_IP=104.131.175.65

echo "🔍 Checking Free Intelligence Server..."
echo ""

# Check container status
echo "🐳 Docker Status:"
ssh -i $SSH_KEY root@$SERVER_IP "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""

# Check backend health
echo "💚 Backend Health:"
ssh -i $SSH_KEY root@$SERVER_IP "curl -s http://localhost:7001/api/health | jq ." 2>/dev/null || \
ssh -i $SSH_KEY root@$SERVER_IP "curl -s http://localhost:7001/api/health"
echo ""

# Check disk space
echo "💾 Disk Usage:"
ssh -i $SSH_KEY root@$SERVER_IP "df -h | grep -E 'Filesystem|/$'"
echo ""

# Check memory
echo "🧠 Memory Usage:"
ssh -i $SSH_KEY root@$SERVER_IP "free -h | grep -E 'total|Mem'"
echo ""

echo "✅ Check complete!"
```

---

## 🎯 Quick Reference

```bash
# Alias para ~/.bashrc
alias fi-ssh='ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65'
alias fi-logs='ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 "docker logs fi-backend --tail 50"'
alias fi-restart='ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 "docker restart fi-backend"'
alias fi-deploy='ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 "cd /opt/free-intelligence && git pull && docker restart fi-backend"'

# Usar
fi-ssh           # Conectar
fi-logs          # Ver logs
fi-restart       # Restart backend
fi-deploy        # Deploy rápido
```

---

## 📚 Resources

- [DigitalOcean SSH Guide](https://docs.digitalocean.com/products/droplets/how-to/connect-with-ssh/)
- [Paramiko Documentation](https://www.paramiko.org/)
- [Docker SSH Guide](https://docs.docker.com/engine/security/protect-access/)

---

**💡 Pro Tip**: Siempre usa SSH keys en lugar de passwords para producción. El password es solo backup de emergencia.
