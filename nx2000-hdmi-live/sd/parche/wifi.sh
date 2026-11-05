#!/bin/sh
# Wi-Fi for the optional Telnet/FTP at boot (flag file parche/wifi-telnet). / Wi-Fi para el Telnet/FTP opcional.
#
# This is remote/connect.sh from hunkreborn's package (mewlips' nx-remote-controller-mod; Copyright 2014 Jonathan
# Dieter, GPL v2 or later) without its ending: it does not open the white window with the IP (yad) and it does not
# simulate the Super_L key (xdotool). The camera takes that key as the shutter pressed halfway ("Key [Id:S1(8)]" in
# the log, 2-3 s after "Current Wi-Fi state: 2"). If it arrives while the HDMI demo is running, the camera turns its
# rear screen back on ("DISPLAY CTRL : ENABLE") and the HDMI output shows that screen, cut into repeated strips.
# Es remote/connect.sh sin la ventana de la IP ni la tecla Super_L, que la cámara toma como el disparador a medias y,
# con la demo HDMI en marcha, estropea la salida.
#
# It still uses remote/disconnect.sh from that package. The IP goes to /mnt/mmc/registros/wifi.txt.
L=/mnt/mmc/registros/wifi.txt
/mnt/mmc/remote/disconnect.sh

/usr/sbin/connmand -W nl80211 -r
/usr/sbin/net-config
dbus-send --system --dest=net.netconfig --print-reply /net/netconfig/wifi net.netconfig.wifi.LoadDriver string:"wifi"
sleep 2

for d in `ls /var/lib/connman`; do
    if [ ! -d "/var/lib/connman/$d" ]; then
        continue
    fi
    echo "Checking stored WiFi connection $d"
    dbus-send --system --print-reply --dest=net.connman "/net/connman/service/$d" net.connman.Service.Connect
    if [ "$?" -eq "0" ]; then
        ip=$(ifconfig wlan0 | grep inet | sed 's/.*addr://' | sed 's/ .*//')
        echo "$(cut -d' ' -f1 /proc/uptime) conectado, IP $ip" >> $L
        exit 0
    fi
done

echo "$(cut -d' ' -f1 /proc/uptime) no se pudo conectar al Wi-Fi" >> $L
exit 1
