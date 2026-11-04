#!/bin/sh
# Live view of the NX2000 on a Linux laptop through a USB HDMI capture card (tested: MacroSilicon 534d:2109).
# Vista en vivo de la NX2000 en la laptop con una capturadora HDMI USB.
#
# The camera outputs a 1920x1080 interlaced HDMI signal with the 720x480 live view in the middle (at 600,300).
# This crops that rectangle and shows it enlarged to 1080x720 (3:2, its real shape), with as little delay as possible.
# La cámara saca una señal 1080 con la imagen de 720x480 en el centro: se recorta y se agranda a 1080x720 (3:2).
#
# IMPORTANT: start this BEFORE plugging the micro HDMI cable into the camera. The MacroSilicon card only asserts
# hot-plug (HPD) while some program is reading from it; without that the camera never sees the cable.
# IMPORTANTE: abrir ANTES de conectar el micro HDMI (la capturadora solo avisa del cable mientras la leen).
#
# Usage / uso: sh ver-en-vivo.sh [x y width height]   (default 600 300 720 480)
# For OBS: use a "Video Capture Device (V4L2)" source and crop 600/300 (left/top), 600/300 (right/bottom).
X=${1:-600}; Y=${2:-300}; W=${3:-720}; H=${4:-480}
D=$(for v in /sys/class/video4linux/video*; do grep -q "USB Video" $v/name && echo /dev/$(basename $v) && break; done)
[ -z "$D" ] && { echo "capture card not found / no se encuentra la capturadora"; exit 1; }
ffmpeg -loglevel quiet -fflags nobuffer -f v4l2 -input_format mjpeg -video_size 1920x1080 -framerate 30 -i $D \
  -vf "crop=$W:$H:$X:$Y,scale=1080:720:flags=lanczos,setsar=1" -c:v rawvideo -pix_fmt yuv420p -f nut \
  -flush_packets 1 pipe:1 \
| ffplay -loglevel quiet -fflags nobuffer -flags low_delay -probesize 32 -analyzeduration 0 -framedrop -sync ext \
  -window_title "Samsung NX2000 live" -x 1080 -y 720 -f nut -i -
