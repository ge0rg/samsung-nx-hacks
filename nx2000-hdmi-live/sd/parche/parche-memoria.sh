#!/bin/sh
# In-memory patches for the NX2000 factory HDMI demo mode (firmware 1.18). Run by autoexec.sh at every boot.
# Parches en memoria para el modo demo HDMI de fábrica de la NX2000 (firmware 1.18). Los lanza autoexec.sh al arrancar.
#
# They only touch the RAM of the running camera program (di-camera-app-nx2000, pid 270): nothing is written to the
# camera's flash, and everything is gone after power-off. Each patch is written ONLY if the original bytes match
# (di-camera-app-nx2000 md5 62d3455d037dd33a86d23f251ccc7d8b); on any other firmware nothing is changed.
#
#  1) 0x1e687c beq -> b: in demo mode, __xrr_output_select takes a "3D" branch that leaves garbage width/height.
#  2) 0x1df020 beq -> b (only if parche/ignorar-desconexion exists): UI_Disconnect_Hdmi ignores HDMI disconnect
#     events (the capture card toggles its hot-plug line).
#  6) (only if parche/demo-2d exists) the demo in 2D:
#     a) 0x1ded8c "bl UI_Set_HDMI_3D_Type" -> nop: avoids set_hdmi() in libmm-displayer, which forces 3D,
#        YCbCr 4:2:2 and 1080p25 (wrong colors / no picture on a capture card). HDMI stays as the kernel sets it (RGB).
#     b) 0x1dedb0 "mov r3, #4" -> "mov r3, #0": mm_camcorder "stereo-video-format" = 0 instead of 4.
L=/mnt/mmc/registros/parche-memoria.txt
mkdir -p /mnt/mmc/registros
P=$(pidof di-camera-app-nx2000)
leer() { dd if=/proc/$P/mem bs=1 skip=$(($1)) count=4 2>/dev/null | od -A n -t x1 | tr -d ' \n'; }
parche() {  # address, expected bytes: turns a conditional branch into an unconditional one (last byte -> 0xea)
  a=$(leer $1)
  [ "$a" = "$2" ] && printf '\352' | dd of=/proc/$P/mem bs=1 seek=$(($1 + 3)) count=1 conv=notrunc 2>/dev/null
  echo "$(cut -d' ' -f1 /proc/uptime) pid $P $1 antes $a despues $(leer $1)" >> $L
}
parche 0x1e687c 1b00000a
[ -e /mnt/mmc/parche/ignorar-desconexion ] && parche 0x1df020 c500000a
if [ -e /mnt/mmc/parche/demo-2d ]; then
  perl -e '
    my $P = shift; open(M, "+<", "/proc/$P/mem") or die $!;
    sub rd { my ($a, $n) = @_; sysseek(M, $a, 0); sysread(M, my $d, $n); return unpack("H*", $d); }
    for my $p ([0x1ded8c, "438cffeb", "0000a0e1"], [0x1dedb0, "0430a0e3", "0030a0e3"]) {
      my ($dir, $orig, $nuevo) = @$p; my $a = rd($dir, 4);
      if ($a eq $orig) { sysseek(M, $dir, 0); syswrite(M, pack("H*", $nuevo)); }
      printf "parche 6 en %x: antes %s despues %s\n", $dir, $a, rd($dir, 4);
    }
  ' $P >> $L 2>&1
fi
sync
