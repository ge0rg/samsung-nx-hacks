# Samsung NX2000: live view over HDMI to a laptop

*(Resumen en español más abajo.)*

Live, stable video from a **Samsung NX2000 (firmware 1.18)** into a laptop through the camera's **micro HDMI** port and
a cheap **USB HDMI capture card** (tested with a MacroSilicon `534d:2109`). Usable as a webcam / for live streaming
with OBS.

Stock NX2000 firmware only uses HDMI to show the photo gallery: when you plug the cable in photo mode it jumps to
playback. This project gets the **live view** out of it instead.

**Result:** full framing, correct aspect ratio and colors, smooth (~24–30 fps), ~0.5–1 s latency, no tearing.
Continuous autofocus works live with the lens AF/MF switch set to AF. It keeps driving the focus motor all the time,
which drains the battery, so **the goal is manual focus with the lens ring** (see To do).

**Limits:**
- DVD-like quality: the source is the 720×480 live-view buffer;
- the camera's own screen goes black while streaming;
- the manual focus ring does not respond;
- the battery drains fast.

## How it works

1. **Hidden factory demo mode.** An empty file `hdmidemo.adj` in the root of the SD card enables a demo mode
   (apparently for 3D TVs at trade shows: `CESDEMO=1`).
   - When HDMI is connected, the camera program switches the memory layout to `mov-hdmi`, restarts the camcorder and
     turns the HDMI/TV output on.
   - It is the only stock path that keeps live view and HDMI running at the same time.
   - Turning HDMI on from normal photo live view (with `xrandr` or by forcing the program's own HDMI routine) crashes
     Xorg on this camera.
2. **In-memory patches** (`sd/parche/parche-memoria.sh`, run at boot from `autoexec.sh`): the demo is made 2D.
   - It skips `UI_Set_HDMI_3D_Type`, whose `set_hdmi()` forces 3D, YCbCr 4:2:2 and 1080p25 (wrong colors / no
     picture on capture cards), and sets `stereo-video-format` to 0.
   - It also ignores HDMI disconnect events, and fixes a 3D branch in `__xrr_output_select`.
   - Nothing is written to the camera's flash: the patches live in RAM, and only if the original bytes match.
3. **Mirror** (`sd/parche/espejo-mem.pl`, started by `esperar-hdmi.sh` when the program logs the HDMI mode change).
   - The landscape live-view frames live in a ring of 3 buffers at physical `0xc74fa000 + k·0x8e000` (720×480 image
     at x=40 inside an 800-byte stride, Y then interleaved CbCr 4:2:0). The rear LCD is a portrait 480×800 panel, so
     what it shows is a rotated copy that cannot be used for TV.
   - The script points the display processor's **TV video window** at the buffer that is complete (it watches which
     one is being written) through `/dev/fb0` ioctls (`DP_IOCTL_TV_VID_SET` / `TV_VID_ADDRESS`).
   - **The demo's HDMI output is interlaced (`1920x1080f`), so the window needs a double stride (1600)**. Without
     it you only see the top half of the picture stretched 2× (it looks zoomed and squeezed).
4. **Laptop** (`laptop/ver-en-vivo.sh`): crops the 720×480 area at (600,300) from the 1080 signal and enlarges it
   with its real 3:2 shape, with low-latency `ffmpeg`/`ffplay` options.

## Requirements

- Samsung NX2000, **firmware 1.18** (other versions: the patch script changes nothing, because it checks the bytes
  first).
- The `nx_cs.adj` trick from [hunkreborn/Samsung-NX2000-Moding-Hack](https://github.com/hunkreborn/Samsung-NX2000-Moding-Hack),
  so the camera runs `autoexec.sh` from the SD card at boot. The camera already has `perl` and `busybox`.
- A USB HDMI capture card and a Linux laptop with `ffmpeg`/`ffplay` (or OBS).

## Install

Copy the contents of `sd/` to the root of the SD card, next to hunkreborn's `nx_cs.adj`:
- `autoexec.sh`;
- `hdmidemo.adj` (empty);
- `parche/` (scripts plus the two empty flag files `demo-2d` and `ignorar-desconexion`);
- `inetd.conf` (only used by the optional Wi-Fi + Telnet, see below).

## Use (order matters)

1. Turn the camera on **without** the HDMI cable (photo mode). The patches are applied and the watcher waits.
2. On the laptop run `sh laptop/ver-en-vivo.sh`. **Open it before plugging the cable:** the MacroSilicon card only
   asserts hot-plug (HPD) while a program is reading from it.
3. Plug the micro HDMI cable. The camera screen goes black and after ~5 s the live view appears on the laptop.
4. Set the lens to **AF** for continuous autofocus.

Closing and reopening the laptop window while the cable is plugged is fine. To get the normal camera back, power it
off **without** the cable and on again. If it does not power off, remove the battery.

## Iterating with an AI agent (optional Wi-Fi + Telnet)

This live view was found by iterating with an AI coding agent: it changes something on the camera, reads the logs
and looks at what reaches the capture card, then tries again. To work the same way:

1. **Enable Wi-Fi + Telnet at boot.** Create an empty file `parche/wifi-telnet` on the SD card.
   - You also need hunkreborn's package: `remote/` (mewlips' remote controller mod, which joins the Wi-Fi network
     saved in the camera) and `inetd.conf` in the SD root (included in `sd/`).
   - Connect the camera to your Wi-Fi once from its own menu so the network is saved.
   - ⚠️ Telnet gives root **without password** and FTP exposes the SD card: only on a trusted network. Remove the flag
     file when you are done (it also saves battery).
2. **Find the camera:** check your router, or ping the subnet and test port 23.
3. **Give the agent these tools:**
   - `python3 tools/nxtel.py <ip> "<command; command>" [seconds]` runs commands (bash on the camera) and prints the
     output. Many systems no longer have a `telnet` client.
   - FTP for files: `curl ftp://<ip>/<path>` downloads and `curl -T file ftp://<ip>/<path>` uploads (the root is
     the SD card).
   - Logs on the SD card, in `registros/`:
     - `arranque-N-dlog.txt`, the camera program log for each boot. It shows, for example, "Mode change succeeded"
       and "hdmi_w";
     - `parche-memoria.txt`, with the bytes before and after each patch;
     - `esperar-hdmi.txt` and `espejo.txt`.
   - The capture card on the laptop, to "see" the output: `ffmpeg -f v4l2 -input_format mjpeg -video_size 1920x1080
     -i /dev/videoN -frames:v 3 -update 1 frame.jpg` (color bars = no signal; black = signal, no image). Remember
     the hot-plug rule above: while a viewer is open, use that viewer's frames instead of reopening the card.
4. **Rules that saved hours:**
   - Read only documented registers, one at a time: `busybox devmem <address>`.
   - Never scan register ranges: it hangs the camera until you pull the battery.
   - The camera program is always pid 270 (it boots from hibernation).
   - Patch RAM through `/proc/270/mem`, and check the original bytes before writing.
   - Use `/proc/*/cmdline` instead of `ps`, which truncates names.
   - Map `/dev/mem` with `O_SYNC` (see `espejo-mem.pl`) to read frames that the hardware writes.

## Findings that may help others

- The camera program (`di-camera-app-nx2000`) keeps its function names in `.dynsym`, for example `UI_Connect_Hdmi`,
  `UI_Set_Hdmi_Connect`, `UI_Hdmi_3D_Liveview` and `__xrr_turn_hdmi_on`.
- The kernel ignores further hot-plug edges after each change until something resets `g_change_hdmi_value`.
- The HDMI PHY/clock is only set up by a DRM mode change. `/dev/HDMI` `START_HDMI` only sets an enable bit.
- **Reading a whole range of display-processor registers with `devmem` hangs the camera.** Read only the documented
  registers. Display processor at `0x500B0000`: TV block at +0x100 (video window address at `0x500B0300`); LCD block
  at +0x600 (video window address at `0x500B0800`).
- Re-reading a DMA buffer with `dd if=/dev/mem` returns stale cached data: map `/dev/mem` with `O_SYNC` instead.
- The kernel sources were essential: [atsidaev/samsung-nx-kernel](https://github.com/atsidaev/samsung-nx-kernel)
  (`include/video/drime4/d4_dp_ioctl.h`, `drivers/video/drime4/tv/d4_dp_tv_reg.h`, `include/video/hdmi/*`).

## To do

- Manual focus with the lens ring, to avoid continuous AF and save battery. In demo mode the ring does not respond
  yet: on NX lenses the ring only sends a signal that the camera program has to act on.
- HD: the 1920×1080 frames exist, but in an internal compressed format (format 4) that the TV window does not show
  as is.
- Clean power-off from demo mode.

## Credits

- [hunkreborn/Samsung-NX2000-Moding-Hack](https://github.com/hunkreborn/Samsung-NX2000-Moding-Hack) (`nx_cs.adj` +
  `autoexec.sh`, prefman codes);
- [ge0rg/samsung-nx-hacks](https://github.com/ge0rg/samsung-nx-hacks) and the
  [HDMI thread #18](https://github.com/ge0rg/samsung-nx-hacks/issues/18);
- mewlips' remote controller mod;
- [atsidaev/samsung-nx-kernel](https://github.com/atsidaev/samsung-nx-kernel).

### How it was done

All the reverse engineering, by [@michumichifu](https://github.com/michumichifu), was done with AI, using
**[Claude Code](https://claude.com/claude-code) (CLI) with Claude Opus 5.5 at *max* effort**:
- disassembling the camera program;
- reading the kernel sources;
- poking registers over Telnet;
- testing live with the capture card.

We started at *high* effort and lost a couple of hours going in circles. Switching to *max* is when the results
came: slower per step, but it got there.

**No warranty.** It works on our NX2000 with firmware 1.18. It patches the running camera program in memory, and a
wrong step can hang the camera until you pull the battery. Use at your own risk.

---

## Resumen en español

**Vídeo en vivo de una Samsung NX2000 (firmware 1.18) en una laptop**, por el micro HDMI de la cámara y una
capturadora HDMI USB. Sirve para transmitir con OBS.

**Resultado:** encuadre completo, proporciones y colores correctos, fluido, con 0,5–1 s de retraso.
- Enfoque automático continuo con la lente en **AF**. Funciona, pero mueve el motor sin parar y gasta batería: el
  objetivo es el **enfoque manual con el anillo** (pendiente).
- Límites: calidad de DVD (720×480), la pantalla de la cámara queda en negro, el anillo de enfoque manual no
  responde y gasta mucha batería.

**Cómo se usa:**
1. Copiar `sd/` a la raíz de la SD, junto al `nx_cs.adj` del mod de hunkreborn.
2. Encender la cámara **sin** el cable.
3. Abrir en la laptop `sh laptop/ver-en-vivo.sh`.
4. **Después**, conectar el micro HDMI.

**Por dentro:**
- `hdmidemo.adj` activa un modo demo de fábrica (pensado para televisores 3D).
- Unos parches en memoria lo dejan en 2D.
- Un script en la cámara (`espejo-mem.pl`) pone en la salida HDMI la imagen en vivo horizontal, con paso doble
  porque la salida es entrelazada.
- La laptop recorta y agranda esa imagen.

**Para iterar con un agente de IA:**
- se puede encender Wi-Fi + Telnet/FTP al arrancar, creando el archivo vacío `parche/wifi-telnet` (necesita el
  paquete de hunkreborn);
- el agente da órdenes con `tools/nxtel.py`, lee los registros de `registros/` en la SD y mira la capturadora con
  `ffmpeg`;
- Telnet entra como root sin clave: solo en una red de confianza;
- reglas que ahorran horas: en la sección "Iterating with an AI agent".

**Cómo se hizo:** con inteligencia artificial, usando **Claude Code (CLI) con Claude Opus 5.5 en esfuerzo *max***.
Empezamos en esfuerzo *high* y perdimos un par de horas. Al pasar a *max* empezaron los resultados: tarda un poco más,
pero llegó.

Los detalles, más arriba en inglés. Sin garantía: probado en una NX2000 con firmware 1.18.
