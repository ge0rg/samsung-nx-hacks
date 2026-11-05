#!/usr/bin/perl
# Manual focus with the lens ring and the AF/MF switch, live during the HDMI demo (NX2000, firmware 1.18).
# Enfoque manual con el anillo y el interruptor AF/MF, en vivo durante la demo HDMI (NX2000, firmware 1.18).
#
# Usage: perl parche-mf.pl <pid of di-camera-app-nx2000> arranque|demo
# Run by parche-memoria.sh (phase "arranque", at boot) and esperar-hdmi.sh (phase "demo", as soon as the demo turns
# HDMI on), only if the flag file /mnt/mmc/parche/enfoque-manual exists.
# Like the other patches, it only touches the RAM of the running program, and each patch is written only if the
# original bytes match.
#
# Why:
# - When HDMI is plugged in, the demo stops the live view, and CCmdLiveview::stop() calls CManualFocus::Prohibit():
#   the lens gets "electric MF prohibited" (the log prints it as "MFRingEventProhibition 1") and nothing grants it
#   again, so the ring does nothing in MF.
# - When it is granted, the lens moves the focus by itself; the camera only gets notices (MF_START, MF_STOP, focus
#   position, MODE_AF/MODE_MF from the switch). In the demo those notices do harm:
#   - the stock program ignores lens notices in the 3D demo ("[Return] Lens: case 3: 3d hdmi liveview"). With patch 6
#     the demo is 2D, that rule no longer applies, and the user interface crashed (do_group_exit(6)) drawing the
#     icons of an AF/MF change (icon 7/14, in 0x186d58);
#   - on MF_START the capture library restarts the live view in "MF mode" (CLiveview::SetMfModeEnable);
#   - from the photo screen, an AF change sends "3A_CAF", which in Program mode only focuses while the shutter is
#     half-pressed. While recording a movie, the same change goes through UI_Manage_Movie_AF and sends "3A_MOVIEAF",
#     which starts continuous AF. The demo is the movie pipeline inside.
#
# Phase "arranque":
#  7) libcapture-fw-slpcam +0x25b538, in CManualFocus::setMFPremission(v): "mov r3, r1" -> "mov r3, #0".
#     Electric MF is always granted.
# Phase "demo":
#  8a) libcapture-fw-slpcam +0x2371e0, CNotifyFromLens::startManualFocus: "bl CManualFocus::Start" -> nop.
#  8b) libcapture-fw-slpcam +0x237208, CNotifyFromLens::stopManualFocus: "bl CManualFocus::Stop" -> nop.
#  9b) di-camera-app-nx2000 0x1f2bdc (20 bytes), UI_Event_Callback_Manager_Lens: instead of checking for the 3D demo
#      (UI_Get_State(0x38) == 1), lens notices 2, 3 and 4 (MODE_AF / MODE_MF, the switch) take the normal path and
#      all the others get the 3D-demo rule ("case 3": ignored, except ids 5 and 0xc).
#  10) di-camera-app-nx2000 0x186d74, in the photo-screen handler of an AF/MF change (0x186d58): "mov r0, #0x79" ->
#      "b 0x186dcc". Skips the four UI_Display_Manage calls (0x79 and icons 7/13, 7/14, 7/23) and 0x187b24 (the
#      focus distance bar).
#  11) di-camera-app-nx2000 0x186e30, same handler, when switching to MF: "beq 0x186e98" -> "b": skips icons 7/6
#      and 7/4.
#  12) di-camera-app-nx2000 0x184308, jump table of UI_Callback_Lens_Focus_Mode (by user interface state): the entry
#      for state 1 (photo screen, 0x1844cc) becomes the one for state 6 (recording a movie, 0x18433c), so the switch
#      goes through UI_Manage_Movie_AF ("3A_MOVIEAF").
#  13) di-camera-app-nx2000 0x1c9d64, 0x1c9db0 and 0x1c9dc4, in UI_Manage_Movie_AF: the three
#      "bl UI_Display_Manage" (icons 7/19, 0x15 and 7/20) -> nop.
# "+" addresses are offsets in libcapture-fw-slpcam-nx2000.so (libcapture-fw-slpcam.so links to it), added to its
# base address from /proc/<pid>/maps. Note that libiq-fw-slpcam.so also has "slpcam" in its name.
# Log: /mnt/mmc/registros/parche-memoria.txt (boot) and esperar-hdmi.txt (demo).
use strict;
my ($P, $fase) = @ARGV;
die "uso: parche-mf.pl <pid> arranque|demo\n" unless $P && $fase;
open(my $maps, "<", "/proc/$P/maps") or die "sin /proc/$P/maps: $!\n";
my $slp;
while (<$maps>) {
  if (/^([0-9a-f]+)-[0-9a-f]+ r-xp 00000000 .*libcapture-fw-slpcam/) { $slp = hex($1); last; }
}
close $maps;
die "no encuentro libcapture-fw-slpcam en /proc/$P/maps\n" unless defined $slp;
my @p = $fase eq "arranque"
  ? ([$slp + 0x25b538, "0130a0e1", "0030a0e3", "7 setMFPremission siempre permite"])
  : ([$slp + 0x2371e0, "2502fceb", "0000a0e1", "8a sin CManualFocus::Start"],
     [$slp + 0x237208, "b7e1fbeb", "0000a0e1", "8b sin CManualFocus::Stop"],
     [0x1f2bdc, "3800a0e3996cfeeb0030a0e1010053e30030a013", "28301be5023043e2020053e32600009a030000ea",
                "9b en la demo la interfaz solo atiende el interruptor AF/MF"],
     [0x186d74,        "7900a0e3", "140000ea", "10 sin iconos ni barra de distancia al cambiar AF/MF"],
     [0x186e30,        "1800000a", "180000ea", "11 sin iconos de modo al pasar a MF"],
     [0x184308,        "cc441800", "3c431800", "12 AF/MF por el camino del video (3A_MOVIEAF)"],
     [0x1c9d64,        "092b01eb", "0000a0e1", "13a sin icono 7/19 en el AF de video"],
     [0x1c9db0,        "f62a01eb", "0000a0e1", "13b sin icono 0x15 en el AF de video"],
     [0x1c9dc4,        "f12a01eb", "0000a0e1", "13c sin icono 7/20 en el AF de video"]);
open(my $M, "+<", "/proc/$P/mem") or die "sin /proc/$P/mem: $!\n";
sub rd { my ($a, $n) = @_; sysseek($M, $a, 0); sysread($M, my $d, $n); return unpack("H*", $d); }
my $t = (split / /, `cat /proc/uptime`)[0];
for my $x (@p) {
  my ($dir, $orig, $nuevo, $nombre) = @$x;
  my $n = length($orig) / 2;
  my $a = rd($dir, $n);
  if ($a eq $orig) { sysseek($M, $dir, 0); syswrite($M, pack("H*", $nuevo)); }
  my $d = rd($dir, $n);
  printf "%s parche %s en %x: antes %s despues %s (%s)\n", $t, $nombre, $dir, $a, $d,
    $d eq $nuevo ? ($a eq $orig ? "puesto" : "ya estaba") : "NO puesto";
}
close $M;
