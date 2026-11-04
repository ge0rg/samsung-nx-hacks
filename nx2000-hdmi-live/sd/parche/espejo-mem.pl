#!/usr/bin/perl
# Espejo de la vista en vivo en la salida HDMI SIN leer registros. Herramienta de Claude; corre en la cámara.
#
# Igual que espejo.pl, pero para cuando la pantalla trasera está apagada (parche 5: la cámara la apaga para poder
# encender el HDMI sin que se caiga Xorg). Con la pantalla apagada no se leen sus registros (podría colgar la cámara),
# así que el búfer listo se deduce mirando la memoria: la cámara escribe la vista en vivo horizontal en un anillo de 3
# búferes (físicas 0xc74fa000, 0xc7588000, 0xc7616000; paso 800; 482 filas; Y y luego C en 4:2:0). Cada pocos
# milisegundos se leen 64 bytes de la fila del medio de cada búfer; el que cambia es el que se está escribiendo, y se
# muestra el anterior, que ya está completo.
#
# Uso: perl espejo-mem.pl [ancho_tv alto_tv] [ancho alto de la imagen] [segundos (0 = sin fin)]
#      foto: 720 480 (desplazada 40 columnas); vídeo: 800 450 (con franjas negras arriba y abajo)
# Registro: /mnt/mmc/registros/espejo.txt
use strict;
use warnings;
use Fcntl;

my $TW  = $ARGV[0] || 1920;
my $TH  = $ARGV[1] || 1080;
my $W   = $ARGV[2] || 720;
my $H   = $ARGV[3] || 480;
my $DUR = $ARGV[4] || 0;
my $ENT = $ARGV[5] || 1;   # 2 = salida entrelazada: la ventana salta de dos en dos líneas (con 1 se ve la mitad de arriba estirada al doble)
my ($HBASE, $HSEP, $HPASO, $HFILAS) = (0xc74fa000, 0x8e000, 800, 482);

open(my $L, ">>", "/mnt/mmc/registros/espejo.txt") or die "registro: $!";
select((select($L), $| = 1)[0]);
sub t { open(my $u, "<", "/proc/uptime"); my $x = <$u>; $x =~ s/ .*//s; $x }
sub log_ { print $L t() . " [mem] " . join("", @_) . "\n"; }

sysopen(my $mem, "/dev/mem", O_RDONLY | O_SYNC) or die "no abre /dev/mem: $!";
open(my $fb, "+<", "/dev/fb0") or die "no abre /dev/fb0: $!";
sub io { my ($nr, $buf) = @_; my $n = 0x40000000 | (length($buf) << 16) | (0x74 << 8) | $nr; return ioctl($fb, $n, $buf); }

sub direcciones {
  my $k = shift;
  my $b = $HBASE + $k * $HSEP;
  my $x = int(($HPASO - $W) / 16) * 8;
  my $y = int((480 - $H) / 2); $y-- if $y % 2;
  return ($b + $y * $HPASO + $x, $b + $HPASO * $HFILAS + ($y / 2) * $HPASO + $x);
}
sub muestra { my $k = shift; sysseek($mem, $HBASE + $k * $HSEP + 240 * $HPASO + 368, 0); sysread($mem, my $d, 64); return $d; }

my ($yd, $cd) = direcciones(0);
my $px = int(($TW - $W) / 4) * 2; my $py = int(($TH - $H) / 2);
my $r = io(57, pack("V5 v x2 V2 V2 V4 V4", 0, 1, 0, 0, 1, $HPASO * $ENT, $W, $H, 4, 0, $yd, $yd + $HPASO, $cd, $cd + $HPASO, $px, $W, $py, $H));
log_ sprintf("inicio: imagen %dx%d en (%d,%d) de %dx%d, paso %d: %s", $W, $H, $px, $py, $TW, $TH, $HPASO * $ENT, defined $r ? "ok" : "fallo $!");
log_ "ventana de vídeo 0 de la TV: " . (defined io(56, pack("LL", 0, 1)) ? "encendida" : "fallo $!");   # TV_VID_WINDOW_ONOFF (sin esto, negro)
log_ "capas: gráficos de la TV " . (defined io(66, pack("L", 0)) ? "apagados" : "fallo $!")
   . ", vídeo encima " . (defined io(62, pack("L", 0)) ? "ok" : "fallo $!");

my @prev = map { muestra($_) } 0 .. 2;
my ($actual, $cambios, $ultimo) = (0, 0, t());
my $fin = $DUR ? t() + $DUR : 0;
while (!$fin || t() < $fin) {
  for my $k (0 .. 2) {
    my $m = muestra($k);
    if ($m ne $prev[$k]) {
      $prev[$k] = $m;
      my $listo = ($k + 2) % 3;                 # el anterior al que se está escribiendo
      if ($listo != $actual) {
        $actual = $listo;
        my ($y, $c) = direcciones($listo);
        io(58, pack("V2 V4 V2", 0, 1, $y, $y + $HPASO, $c, $c + $HPASO, 0, 0));
        $cambios++;
      }
    }
  }
  if (t() - $ultimo >= 10) { log_ "cuadros en 10 s: $cambios"; $cambios = 0; $ultimo = t(); }
  select(undef, undef, undef, 0.006);
}
log_ "fin";
