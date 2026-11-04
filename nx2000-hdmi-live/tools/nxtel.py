# Minimal Telnet client to script the camera (many systems no longer ship a telnet client).
# Cliente Telnet mínimo para dar órdenes a la cámara desde scripts o desde un agente de IA.
# Usage / uso: python3 -I nxtel.py <ip> "<command; command>" [seconds_to_wait]
# It refuses every Telnet option, sends the command line, waits and prints the output.
import socket, sys, time

IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240

def limpiar(data, s):
    out = bytearray(); i = 0
    while i < len(data):
        b = data[i]
        if b == IAC and i + 1 < len(data):
            c = data[i + 1]
            if c in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                opt = data[i + 2]
                s.sendall(bytes([IAC, WONT if c in (DO, DONT) else DONT, opt]))
                i += 3; continue
            if c == SB:
                j = data.find(bytes([IAC, SE]), i)
                i = (j + 2) if j >= 0 else len(data); continue
            i += 2; continue
        out.append(b); i += 1
    return bytes(out)

def leer(s, espera):
    s.settimeout(0.5); buf = bytearray(); fin = time.time() + espera
    while time.time() < fin:
        try:
            d = s.recv(65536)
            if not d: break
            buf += limpiar(d, s)
        except socket.timeout:
            pass
    return buf.decode('utf-8', 'replace')

ip, orden = sys.argv[1], sys.argv[2]
espera = float(sys.argv[3]) if len(sys.argv) > 3 else 4
s = socket.create_connection((ip, 23), timeout=10)
leer(s, 2)                                   # greeting and options / saludo y opciones
s.sendall(orden.encode() + b"\n")
print(leer(s, espera))
s.sendall(b"exit\n")
s.close()
