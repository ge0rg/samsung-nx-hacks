#!/bin/sh
# Low-latency live view of the NX2000 on a Linux laptop, with GStreamer (recommended over ver-en-vivo.sh).
# Vista en vivo con poco retraso, con GStreamer (recomendada frente a ver-en-vivo.sh).
#
# ver-en-vivo.sh (ffmpeg piping raw frames into ffplay) ended up 2-3 s behind on our laptop, with plenty of CPU left:
# frames piled up between the two programs. This is a single program that shows each frame as soon as it arrives
# (sync=false) and keeps queues of one frame that drop old ones (leaky). Measured: ~0.3-0.6 s, stable; ~15-20 % of
# one CPU core.
# Con ver-en-vivo.sh el retraso llegaba a 2-3 s; con esta, ~0,3-0,6 s.
#
# IMPORTANT: start this BEFORE plugging the micro HDMI cable into the camera (the MacroSilicon card only asserts
# hot-plug while some program is reading from it). Closing it with the cable plugged in is, for the camera, an unplug.
# IMPORTANTE: abrir ANTES de conectar el micro HDMI.
#
# Usage / uso: sh ver-en-vivo-gst.sh [x y width height]   (default 600 300 720 480)
# Environment / variables:
#   M=lanczos|4-tap|bilinear  scaling method (default lanczos, ~3 ms per frame)
#   SNAP=/path/frame.jpg      also save one full 1920x1080 frame per second (to check what the card receives)
# On Wayland, the window is opened through X (GST_GL_WINDOW=x11) so that it gets a title bar and can be moved and
# resized; wmctrl, if installed, renames it.
X=${1:-600}; Y=${2:-300}; W=${3:-720}; H=${4:-480}; M=${M:-lanczos}
D=$(for v in /sys/class/video4linux/video*; do grep -q "USB Video" $v/name && echo /dev/$(basename $v) && break; done)
[ -z "$D" ] && { echo "capture card not found / no se encuentra la capturadora"; exit 1; }
export GST_GL_WINDOW=x11
if command -v wmctrl >/dev/null; then
  (i=0; while [ $i -lt 30 ]; do sleep 0.5; i=$((i + 1))
     w=$(wmctrl -l 2>/dev/null | grep -m1 "OpenGL renderer" | cut -d' ' -f1)
     [ -n "$w" ] && wmctrl -i -r $w -N "Samsung NX2000 live" && break
   done) &
fi
VIEW="queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream \
  ! videocrop left=$X top=$Y right=$((1920 - X - W)) bottom=$((1080 - Y - H)) \
  ! videoscale method=$M ! video/x-raw,width=1080,height=720,pixel-aspect-ratio=1/1 \
  ! videoconvert ! glimagesink sync=false qos=false force-aspect-ratio=true"
if [ -n "$SNAP" ]; then
  exec gst-launch-1.0 -q v4l2src device=$D ! image/jpeg,width=1920,height=1080,framerate=30/1 ! jpegdec \
    ! tee name=t t. ! $VIEW \
    t. ! queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream \
       ! videorate drop-only=true ! video/x-raw,framerate=1/1 ! jpegenc quality=85 \
       ! multifilesink location="$SNAP" sync=false async=false
else
  exec gst-launch-1.0 -q v4l2src device=$D ! image/jpeg,width=1920,height=1080,framerate=30/1 ! jpegdec ! $VIEW
fi
