# AIRE en Azure — runbook (SSH + grep, la meta)

El daemon (`aire-listener`) y el device simulado (`aire-demo-device`) corren como
servicios systemd en una VM Linux de Azure, 24/7, escribiendo a un log append-only.
Entras por SSH y lo grepeas — la experiencia de EC-GPS, recreada.

## Entrar y ver los logs

```bash
ssh azureuser@<IP>                                    # <IP> la imprime azure-vm.sh

tail -f /opt/aire/aire.log                            # todo, en vivo
tail -f /opt/aire/aire.log | grep KEEPALIVE           # los latidos
grep MESSAGE /opt/aire/aire.log | tail -50            # los mensajes random
wc -l /opt/aire/aire.log                              # cuántas líneas lleva el día
```

## Operar los servicios

```bash
sudo systemctl status aire-listener aire-demo-device
sudo journalctl -u aire-listener -f                   # logs del propio daemon
sudo systemctl restart aire-demo-device               # reiniciar el device
```

## Redeploy (tras un push al repo)

```bash
curl -fsSL https://raw.githubusercontent.com/BernardUriza/aire-server/main/deploy/setup.sh | sudo bash
```

## Apagar / borrar todo (cuando quieras, para de cobrar)

```bash
az group delete -n aire-rg --yes --no-wait
```
