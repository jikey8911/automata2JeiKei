# Uso temporal de tu PC como proxy para ccxt/exchanges

## En tu PC (Windows)
1. Instala una app de proxy SOCKS (ej. SocksDroid en Android; en Windows puedes usar 3proxy o ssh -D).
2. Expone el proxy en la IP Tailscale de tu PC (ej. 100.90.90.65) y puerto 1080.
3. Asegúrate de que el firewall permita el puerto 1080 en la interfaz Tailscale.

## En el servidor (Oracle)
1. Exporta las variables de proxy solo para ccxt/supervisor:
   `ash
   export HTTP_PROXY=socks5://100.90.90.65:1080
   export HTTPS_PROXY=socks5://100.90.90.65:1080
   `
2. Reinicia el supervisor para que herede las vars:
   `ash
   cd /home/ubuntu/automata2JeiKei
   docker compose restart supervisor
   `
3. Verifica IP de salida desde el contenedor supervisor:
   `ash
   docker exec -it automata_supervisor curl -s https://api.ipify.org
   `

## Importante
- Si tu PC se apaga o se suspende, el proxy caerá y ccxt volverá a fallar.
- Cuando tengas un VPS/exit node dedicado, cambia las variables HTTP(S)_PROXY a ese host.
