# 🌊 DigitalOcean Mini Certificación - Cloud Simplificado

## 📚 Módulo 1: Fundamentos DigitalOcean (20 min)

### 1.1 ¿Por qué DigitalOcean?
```yaml
Ventajas sobre AWS:
✅ Precios transparentes (sin sorpresas)
✅ UI/UX 10x más simple
✅ Acepta PayPal
✅ Documentación clara
✅ Comunidad increíble
✅ $200 USD créditos gratis
```

### 1.2 Conceptos Core
```yaml
Droplets:        VPS (servidores virtuales)
Spaces:          Almacenamiento S3-compatible
App Platform:    PaaS serverless (como Heroku)
Databases:       PostgreSQL, MySQL, Redis gestionado
Kubernetes:      K8s gestionado
Load Balancers:  Balanceadores de carga
Volumes:         Almacenamiento en bloque
```

### 1.3 Regiones Disponibles
```yaml
NYC (New York):  Mejor para México (latencia ~40ms)
SFO (San Francisco): Costa oeste
TOR (Toronto):   Canadá
LON (London):    Europa
AMS (Amsterdam): Europa
SGP (Singapore): Asia
```

### 📝 Quiz 1
1. ¿Qué es un Droplet?
   - [x] Servidor virtual (VPS)
   - [ ] Base de datos
   - [ ] Almacenamiento

2. ¿Cuál región es mejor para México?
   - [x] NYC (New York)
   - [ ] LON (London)
   - [ ] SGP (Singapore)

---

## 🖥️ Módulo 2: Droplets - Tu Servidor (30 min)

### 2.1 Tipos de Droplets
```bash
# Basic (Shared CPU) - Perfectos para empezar
s-1vcpu-512mb    $4/mes   # Muy básico
s-1vcpu-1gb      $6/mes   # RECOMENDADO para tu app
s-1vcpu-2gb      $12/mes  # Con más RAM
s-2vcpu-2gb      $18/mes  # Más poder

# Premium (Dedicated CPU) - Para producción
c-2              $42/mes  # 2 vCPU dedicados
c-4              $84/mes  # 4 vCPU dedicados
```

### 2.2 Crear Droplet con doctl
```bash
# Instalar doctl
brew install doctl

# Autenticar
doctl auth init

# Crear SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/do_key

# Subir SSH key
doctl compute ssh-key import my-key --public-key-file ~/.ssh/do_key.pub

# Crear Droplet
doctl compute droplet create my-droplet \
  --region nyc3 \
  --size s-1vcpu-1gb \
  --image ubuntu-22-04-x64 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Listar Droplets
doctl compute droplet list

# SSH al Droplet
ssh root@<IP_ADDRESS>
```

### 2.3 Configurar Firewall
```bash
# Crear firewall
doctl compute firewall create \
  --name web-firewall \
  --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0 protocol:tcp,ports:80,address:0.0.0.0/0 protocol:tcp,ports:443,address:0.0.0.0/0" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0 protocol:udp,ports:all,address:0.0.0.0/0"

# Asignar a Droplet
doctl compute firewall update <firewall-id> \
  --droplet-ids <droplet-id>
```

### 📝 Lab 1: Deploy Backend en Droplet
```bash
# 1. Crear Droplet con Docker pre-instalado
doctl compute droplet create backend \
  --region nyc3 \
  --size s-1vcpu-1gb \
  --image docker-20-04 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# 2. SSH y deploy
ssh root@<IP>

# 3. Clonar y correr
git clone https://github.com/tu-repo/free-intelligence.git
cd free-intelligence
docker build -t backend .
docker run -d -p 7001:7001 backend

# 4. Verificar
curl http://<IP>:7001/api/health
```

---

## 📦 Módulo 3: Spaces - Almacenamiento (20 min)

### 3.1 Spaces = S3 Compatible
```python
# Python ejemplo con boto3
import boto3

# Configurar cliente
client = boto3.client('s3',
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id='DO_ACCESS_KEY',
    aws_secret_access_key='DO_SECRET_KEY'
)

# Crear bucket
client.create_bucket(Bucket='mi-audio-bucket')

# Subir archivo
client.upload_file(
    'audio.mp3',
    'mi-audio-bucket',
    'sessions/audio.mp3'
)

# Generar URL temporal
url = client.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'mi-audio-bucket', 'Key': 'audio.mp3'},
    ExpiresIn=3600
)
```

### 3.2 CDN Incluido
```bash
# URL normal
https://mi-bucket.nyc3.digitaloceanspaces.com/file.mp3

# URL con CDN (más rápido)
https://mi-bucket.nyc3.cdn.digitaloceanspaces.com/file.mp3
```

### 3.3 Costos
```yaml
Storage:      $5/mes por 250GB
Transfer:     $0.01/GB después de 1TB gratis
CDN:          GRATIS
```

---

## 🚀 Módulo 4: App Platform - Serverless (25 min)

### 4.1 ¿Qué es App Platform?
```yaml
Concepto: PaaS como Heroku, pero más barato
Ventajas:
- Deploy desde GitHub (automático)
- Auto-scaling
- HTTPS gratis
- Logs centralizados
- Sin mantener servidores

Ideal para:
- APIs REST
- Aplicaciones web
- Microservicios
```

### 4.2 Deploy desde GitHub
```yaml
# app.yaml
name: mi-backend
region: nyc
services:
- name: api
  github:
    repo: usuario/free-intelligence
    branch: main
    deploy_on_push: true
  dockerfile_path: Dockerfile
  instance_count: 1
  instance_size_slug: basic-xxs  # $5/mes
  http_port: 7001
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}
    type: SECRET

databases:
- name: db
  engine: PG
  version: "15"
  size: db-s-dev-database  # $7/mes
```

```bash
# Deploy
doctl apps create --spec app.yaml

# Ver logs
doctl apps logs <app-id>

# Escalar
doctl apps update <app-id> --spec app.yaml
```

### 4.3 CI/CD Automático
```yaml
GitHub Push → App Platform detecta → Build → Deploy → Live!

Sin configuración adicional
Sin Jenkins, sin GitHub Actions
Todo automático
```

---

## 💰 Módulo 5: Optimización de Costos (15 min)

### 5.1 Calculadora Real
```yaml
Tu App (Mínimo viable):
- Droplet s-1vcpu-1gb:     $6/mes
- Spaces (100GB):           $5/mes
- Database Dev:             $7/mes
TOTAL:                      $18/mes

Tu App (Producción):
- App Platform (2 instances): $10/mes
- Database Production:        $15/mes
- Spaces + CDN:              $5/mes
- Load Balancer:             $12/mes
TOTAL:                       $42/mes

AWS Equivalente:             ~$65-80/mes
```

### 5.2 Trucos para Ahorrar
```bash
# 1. Snapshots en lugar de backups
doctl compute droplet-action snapshot <droplet-id>
# $0.05/GB vs $1/GB backup

# 2. Reserved IPs gratis (si están en uso)
doctl compute floating-ip create --region nyc3

# 3. Volumes compartidos
doctl compute volume create my-volume --size 10 --region nyc3

# 4. Apagar Droplets de desarrollo
doctl compute droplet-action shutdown <droplet-id>
```

### 5.3 Monitoreo de Costos
```bash
# Ver billing actual
doctl billing-history list

# Alertas
doctl monitoring alert create \
  --name "Billing Alert" \
  --type "billing" \
  --value 50 \
  --emails "tu@email.com"
```

---

## 🔧 Módulo 6: Terraform para DO (20 min)

### 6.1 Configuración Básica
```hcl
terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

variable "do_token" {
  description = "DigitalOcean API Token"
}
```

### 6.2 Crear Infraestructura Completa
```hcl
# Droplet
resource "digitalocean_droplet" "web" {
  name   = "mi-servidor"
  region = "nyc3"
  size   = "s-1vcpu-1gb"
  image  = "ubuntu-22-04-x64"
}

# Database
resource "digitalocean_database_cluster" "postgres" {
  name       = "mi-db"
  engine     = "pg"
  version    = "15"
  size       = "db-s-dev-database"
  region     = "nyc3"
  node_count = 1
}

# Spaces
resource "digitalocean_spaces_bucket" "assets" {
  name   = "mi-bucket"
  region = "nyc3"
  acl    = "private"
}
```

### 6.3 Deploy con Terraform
```bash
# Inicializar
terraform init

# Plan
terraform plan

# Aplicar
terraform apply

# Destruir (cuando termines)
terraform destroy
```

---

## 🎯 Proyecto Final: Deploy Completo

### Requisitos
- [ ] Backend en App Platform o Droplet
- [ ] Frontend en Spaces (sitio estático)
- [ ] Database PostgreSQL
- [ ] Dominio personalizado (opcional)

### Pasos
```bash
# 1. Crear cuenta DigitalOcean
https://www.digitalocean.com/

# 2. Obtener API Token
https://cloud.digitalocean.com/account/api/tokens

# 3. Configurar doctl
doctl auth init

# 4. Deploy backend
./scripts/deploy-digitalocean.sh

# 5. Verificar
curl https://tu-app.ondigitalocean.app/api/health
```

---

## 🏆 Examen Final

### Pregunta 1
¿Cuánto cuesta un Droplet básico?
```
a) $4/mes (512MB RAM)
b) $6/mes (1GB RAM) ✅
c) $12/mes (2GB RAM)
d) $20/mes (4GB RAM)
```

### Pregunta 2
¿Qué comando crea un Droplet?
```bash
doctl compute droplet create nombre \
  --region nyc3 \
  --size s-1vcpu-1gb \
  --image ubuntu-22-04-x64
```

### Pregunta 3
¿Cuál es la ventaja principal de App Platform?
```
a) Más barato
b) Más rápido
c) No necesitas mantener servidores ✅
d) Más seguro
```

### Lab Final
Deploy tu app y comparte:
- [ ] URL funcionando
- [ ] Screenshot del dashboard DO
- [ ] Costo mensual estimado

---

## 📜 Certificado

```
╔═══════════════════════════════════════════════════╗
║                                                   ║
║        DIGITALOCEAN CLOUD PRACTITIONER           ║
║           Free Intelligence Edition              ║
║                                                   ║
║  Certificamos que: _________________________     ║
║                                                   ║
║  Ha completado con éxito:                        ║
║  • Droplets & Compute                           ║
║  • Spaces & Storage                             ║
║  • App Platform                                 ║
║  • Databases                                    ║
║  • Infrastructure as Code                       ║
║                                                   ║
║  Fecha: _______________                          ║
║  ID: DO-FI-2024-001                             ║
║                                                   ║
║      🌊 Ready for Production on DO! 🌊          ║
╚═══════════════════════════════════════════════════╝
```

## 🎁 Recursos Gratuitos

1. **$200 USD Créditos**: https://try.digitalocean.com/freetrialoffer
2. **GitHub Student**: $200 extra si eres estudiante
3. **Hatch Startup Program**: $5000 créditos para startups
4. **Tutorial Community**: 4000+ tutoriales gratis
5. **DO Calculator**: https://www.digitalocean.com/pricing/calculator

## 🚀 Siguiente Paso

```bash
# 1. Crear cuenta (acepta PayPal!)
https://www.digitalocean.com/

# 2. Obtén $200 gratis
Usa referral o GitHub Student Pack

# 3. Deploy hoy mismo
doctl auth init
./scripts/deploy-digitalocean.sh
```

**Tiempo total**: 2 horas
**Resultado**: App en producción pagando con PayPal 🎉

---

💡 **Pro Tip**: DigitalOcean es el cloud favorito de developers independientes y startups. Es 70% más simple que AWS y 50% más barato. La comunidad es increíble y siempre ayudan. ¡Bienvenido al cloud que sí funciona con México!
