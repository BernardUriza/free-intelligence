# Arbor TTS on Azure VM

This deploys `arbor-tts` as a small Ubuntu VM in `insult-rg`.

## Shape

- Azure VM: `arbor-tts-vm`
- App: Node service on `127.0.0.1:8799`
- Reverse proxy: nginx on ports `80`/`443`
- Process manager: `systemd` unit `arbor-tts`
- Auth: `SERVICE_TOKEN` in `/opt/arbor-tts/.env`

Keep `8799` closed. Only expose nginx, and restrict the NSG source CIDR when
possible.

## Create VM

```bash
cd infra/azure/arbor-tts
SSH_SOURCE_CIDR="$(curl -s https://ifconfig.me)/32" ./create-vm.sh
```

Optional:

```bash
HTTPS_SOURCE_CIDR="x.x.x.x/32" ./create-vm.sh
VM_SIZE=Standard_B2ms ./create-vm.sh
```

## Deploy App

```bash
HOST=<vm-public-ip> ./deploy-app.sh
```

For production calls, point a DNS name at the VM public IP and enable TLS:

```bash
HOST=<vm-public-ip> DOMAIN=tts.example.com EMAIL=you@example.com ./enable-tls.sh
```

Then create `/opt/arbor-tts/.env` on the VM:

```bash
sudo cp /opt/arbor-tts/.env.example /opt/arbor-tts/.env
sudo nano /opt/arbor-tts/.env
sudo chown arbor:arbor /opt/arbor-tts/.env
sudo systemctl restart arbor-tts
```

Minimum production-ish values:

```env
PORT=8799
HEADLESS=1
AUTH_STATE=./auth/state.json
ARBOR_VOICE=arbor
ARBOR_FORMAT=mp3
MAX_TEXT_CHARS=4096
REQUIRE_SERVICE_TOKEN=1
SERVICE_TOKEN=<long-random-token>
TTS_ENABLED=1
RATE_LIMIT_WINDOW_MS=3600000
RATE_LIMIT_MAX_REQUESTS=20
DAILY_REQUEST_CAP=100
DAILY_TEXT_CHAR_CAP=100000
CALLBACK_ALLOWLIST=
```

## ChatGPT Login State

Run login locally and upload only the Playwright auth state:

```bash
cd arbor-tts
npm run login
scp auth/state.json azureuser@<vm-public-ip>:/tmp/state.json
ssh azureuser@<vm-public-ip> 'sudo mkdir -p /opt/arbor-tts/auth && sudo mv /tmp/state.json /opt/arbor-tts/auth/state.json && sudo chown -R arbor:arbor /opt/arbor-tts/auth && sudo systemctl restart arbor-tts'
```

## Use from Container Apps

Set these env vars on the bot Container App:

```env
ARBOR_TTS_URL=https://<your-tts-domain>
ARBOR_TTS_TOKEN=<same SERVICE_TOKEN>
ARBOR_TTS_VOICE=arbor
ARBOR_TTS_TIMEOUT_SECONDS=240
```

With `ARBOR_TTS_URL` set, the Discord `🔊` reaction path uses Arbor TTS. Without
it, it falls back to Azure OpenAI speech.

## Callback Mode

`arbor-tts` can also deliver audio to one of your endpoints:

```json
{
  "text": "hola",
  "voice": "arbor",
  "format": "mp3",
  "request_id": "abc123",
  "callback_url": "https://your-service.example/tts-ready",
  "callback_headers": {
    "authorization": "Bearer <token>"
  }
}
```

The callback receives JSON with `audio_base64`, `content_type`, `bytes`,
`voice_id`, `voice_name`, and `request_id`. Callback hosts are denied unless
`CALLBACK_ALLOWLIST` includes the hostname, for example:

```env
CALLBACK_ALLOWLIST=discord-bot.nicecliff-10074f57.eastus.azurecontainerapps.io,*.azurecontainerapps.io
```
