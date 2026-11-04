#!/bin/sh
# Herramienta de Claude (versión para el arranque).
# Con la demo en 2D (hdmidemo.adj + parche 6), al conectar el micro HDMI la cámara enciende ella misma la salida
# ("hdmi_w", "Mode change succeeded"). Este vigilante espera ese momento en el registro del programa y arranca
# espejo-mem.pl con el tamaño de salida que eligió la cámara ("Selected index N : WxH") y la imagen de vídeo entera
# (720x480, que es 16:9 comprimida a lo ancho: la ventana de la laptop la estira).
# Lo lanza autoexec.sh al encender (en segundo plano) y espera sin límite. También se puede lanzar a mano.
# Registro: /mnt/mmc/registros/esperar-hdmi.txt
L=/mnt/mmc/registros/esperar-hdmi.txt
W=${W:-720}; H=${H:-480}
n=$(ls /mnt/mmc/registros | grep -o "arranque-[0-9]*" | sort -t- -k2 -n | tail -1)
F=/mnt/mmc/registros/$n-dlog.txt
i=0; while [ ! -s $F ] && [ $i -lt 60 ]; do sleep 1; i=$((i + 1)); done
desde=$(wc -l < $F 2>/dev/null); [ -z "$desde" ] && desde=1
echo "=== $(cut -d' ' -f1 /proc/uptime) esperando el HDMI en $F desde la línea $desde (imagen ${W}x${H})" >> $L
while true; do
  if tail -n +$desde $F | grep -q "hdmi_w\|__xrr_turn_hdmi_on"; then
    sleep 4
    tail -n +$desde $F | grep "hdmi_w\|Selected index\|__xrr_turn_hdmi_on\|Mode [Cc]hange" | cut -c1-120 >> $L
    S=$(tail -n +$desde $F | grep -o "Selected index [0-9]* : [0-9]*x[0-9]*" | tail -1 | grep -o "[0-9]*x[0-9]*$")
    TW=${S%x*}; TH=${S#*x}; [ -z "$S" ] && TW=1920 && TH=1080
    echo "salida ${TW}x${TH}; conector $(cat /sys/class/drm/card0-HDMI-A-1/status); Xorg $(pidof Xorg)" >> $L
    nohup perl /mnt/mmc/parche/espejo-mem.pl $TW $TH $W $H 0 ${ENT:-2} >/dev/null 2>&1 &
    sleep 2; tail -3 /mnt/mmc/registros/espejo.txt >> $L
    sync
    exit 0
  fi
  sleep 1
done
