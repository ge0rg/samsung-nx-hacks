import struct
      
window = bytearray(b'\x00' * 8192) # TODO size

def print(foo):
    pass

def decode_block(f, f_out=None):
    flag_bytes = f.read(2)
    flag = struct.unpack(">H", flag_bytes)[0]
    bitmask = format(flag, "016b")
    print(f"bitmask {bytes.hex(flag_bytes)} {bitmask}")
    for bit in bitmask:
        if bit == '0':
            literal = f.read(1)
            print(f"literal {bytes.hex(literal)}")
            window.extend(literal)
            if f_out:
                f_out.write(literal)
        else:
            ofshi_len, ofslo = struct.unpack("2B", f.read(2))
            # TODO: is it really 3bit/13bit offset/len 0bOOOO'OLLL'OOOO'OOOO?
            token_len = 3 + (ofshi_len & 0x07) 
            offset = ((ofshi_len >> 3) << 8) + ofslo
            print(f"token {token_len} at -{offset:x}")
            lookup = bytearray()
            lookup.extend(window[-offset:-offset+token_len])
            window.extend(lookup)
            print(f"lookup {bytes.hex(bytes(lookup))}")
            if f_out:
                f_out.write(bytes(lookup))


f_in = open("chunk-05.bin", "rb")
f_in.seek(2)
f_out = open("chunk-05.raw", "wb")

while True:
    decode_block(f_in, f_out)
