#!/bin/sh
# NX2000 live HDMI view (firmware 1.18). Executed at boot by the camera when nx_cs.adj is on the SD card
# (see hunkreborn/Samsung-NX2000-Moding-Hack). Vista en vivo por HDMI de la NX2000.

# The camera program log is needed: esperar-hdmi.sh watches it to know when the HDMI output is up.
# El registro del programa hace falta: esperar-hdmi.sh lo vigila para saber cuándo se enciende el HDMI.
mkdir -p /mnt/mmc/registros
n=$(ls /mnt/mmc/registros | grep -c dlog)
dlogutil -v time -f /mnt/mmc/registros/arranque-$n-dlog.txt &

# In-memory patches (1, 2 and 6) / parches en memoria
/mnt/mmc/parche/parche-memoria.sh

# Waits for the HDMI connection and starts the mirror / espera el HDMI y arranca el espejo
[ -e /mnt/mmc/parche/demo-2d ] && sh /mnt/mmc/parche/esperar-hdmi.sh &

# OPTIONAL: Wi-Fi + Telnet/FTP at boot, to iterate and debug (for example with an AI agent). Enable it by creating an
# empty file parche/wifi-telnet. Needs hunkreborn's package (remote/ = mewlips' nx-remote-controller-mod, which
# joins the Wi-Fi network saved in the camera) and inetd.conf. Telnet is root WITHOUT password and FTP exposes the
# SD card: use it only on a trusted network. It also costs battery.
# OPCIONAL: Wi-Fi + Telnet/FTP al arrancar, para iterar y depurar (por ejemplo con un agente de IA). Se activa
# creando el archivo vacío parche/wifi-telnet. Telnet entra como root SIN clave: solo en una red de confianza.
if [ -e /mnt/mmc/parche/wifi-telnet ]; then
  mkdir -p /dev/pts
  mount -t devpts none /dev/pts
  inetd /mnt/mmc/inetd.conf
  /mnt/mmc/remote/start.sh
  /mnt/mmc/remote/connect.sh
fi
