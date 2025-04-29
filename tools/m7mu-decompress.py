#!/usr/bin/env python3

import os
import struct
import sys
from argparse import ArgumentParser

def auto_int(x):
    return int(x, 0)

parser = ArgumentParser()
parser.add_argument('filename', metavar='FILE.bin',
                    help='firmware file to decompress')
parser.add_argument('-o', '--output',
                    dest='fn_out', default=False,
                    help='output file to decompress into')
parser.add_argument('-O', '--offset',
                    type=auto_int, dest='offset', default=0,
                    help='offset in input file to start decoding at')
parser.add_argument('-W', '--window',
                    type=auto_int, dest='window', default=-1,
                    help='window size for decompression (<0 - uncompressed stream; >0 - ring buffer)')
parser.add_argument('-d', '--debug',
                    action='store_true', dest='debug', default=False,
                    help='emit debug output')
args = parser.parse_args()

OFS_BITS = 3

class RingBufferWindow(bytearray):
    def __init__(self, winsize):
        super().__init__(b'\x00'*winsize)
        self.winsize = winsize
        self.window_idx = 0

    def extend(self, data):
        for d in data:
            self[self.window_idx] = d
            self.window_idx = (self.window_idx + 1 ) % self.winsize

    def get(self, offset, count):
        result = bytearray()
        for i in range(count):
            result.append(self[(self.window_idx + self.winsize - offset + i) % self.winsize])
        return result

class AppendWindow(bytearray):
    def __init__(self, winsize):
        super().__init__()
        self.winsize = winsize

    def extend(self, data):
        # TODO: remove the beginning to preserve RAM
        super().extend(data)

    def get(self, offset, count):
        if offset == count:
            end = None
        else:
            end = -offset+count
        return self[-offset:end]

if args.window < 0:
    window = AppendWindow(-args.window)
else:
    window = RingBufferWindow(args.window)

block_idx = 0

def x(ba):
    '''helper to output hex/readable output'''
    if type(ba) == bytearray:
        ba = bytes(ba)
    return ba.__repr__()

def xb(ba):
    '''helper to output hex/readable output'''
    bax = bytes.hex(ba)
    bab = "'".join([format(int(nibble, 16), "04b") for nibble in bax])
    return f"0x{bax}={bab}b"

def dprint(*a):
    '''debug print'''
    if args.debug:
        print(*a)

def decode_block(f, f_out=None, max_in=None):
    '''read a 16-bit flag from file f, read and decode the following data accordingly'''
    global block_idx
    ofs =f.tell()
    flag_bytes = f.read(2)
    flag = struct.unpack(">H", flag_bytes)[0]
    bitmask = format(flag, "016b")
    bitmask1 = bitmask + "1" # used to find() streaks of 0s
    dprint(f"{ofs:08x} ({block_idx}): bitmask {xb(flag_bytes)} max={max_in}")
    block_idx = block_idx + 1
    i = 0
    out_len = 0
    while i < 16:
        _in = f.tell()-ofs
        if _in > max_in:
            raise IndexError(f"{ofs:08x} read {_in} instead of allowed {max_in} bytes")
        bit = bitmask[i]
        if bit == '0':
            # obtain number of consecutive 0 bits in flag -> number of literal bytes
            literal_len = bitmask1.find("1", i) - i
            if literal_len > max_in-_in:
                raise IndexError(f"{ofs:08x} literal has {literal_len} instead of allowed {max_in-_in} bytes")
            literal = f.read(literal_len)
            dprint(f"    literal {x(literal)}")
            window.extend(literal)
            if f_out:
                f_out.write(literal)
            i += literal_len
            out_len += literal_len
        else:
            # read 2-byte flag and decode offset and length
            mask = f.read(2)
            ofshi_len, ofslo = struct.unpack("2B", mask)
            token_len = 3 + (ofshi_len & ((1 << OFS_BITS)-1))
            offset = ((ofshi_len >> OFS_BITS) << 8) + ofslo
            if mask == b'\x00\x00':
                dprint(f"    Encountered EOB 0x0000 token")
                return out_len
            if token_len == 10:
                # variable length token with additional length bytes: read until != 255
                vlb = 255
                while vlb == 255:
                    if _in+len(mask) >= max_in:
                        dprint(f"    can't read token byte #{len(mask)} due to EOB")
                        break
                    vlb = f.read(1)[0]
                    mask = mask + bytes([vlb])
                    # the additional byte gets added to the length
                    token_len = token_len + vlb
            dprint(f"    token   {xb(mask)}: {token_len} at -{offset}")
            #TODO: can we use this to validate "good" vs. bad offsets?
            if offset > len(window):
                raise IndexError(f"{ofs:08x}: trying to look back {offset} bytes in a {len(window)}-sized window")
            # VARIANT A: first get the bytes from the old window, then extend the window
            #lookup = window.get(offset, token_len)
            #window.extend(lookup)
            # VARIANT B: extend the window byte-by-byte to prevent feeding old bytes when offset < token_len
            lookup = bytearray()
            for l in range(token_len):
                nxt = window.get(offset, 1)
                lookup.extend(nxt)
                window.extend(nxt)
            #if offset < token_len:
            #    raise IndexError(f"{ofs:08x}: trying to look back {offset} bytes for a {token_len} token")
            dprint(f"        --> {x(bytes(lookup))}")
            #dprint(f"        --> {x(bytes(lookup))} -- {x(window.get(offset, 16))}")
            if f_out:
                f_out.write(bytes(lookup))
            i += 1
            out_len += len(lookup)
    return out_len

def decode_range(f, f_out=None):
    '''decode a subsection from a file, starting with a flag+length, then (un)compressed, then EOB=0x0000'''
    f_pos = f.tell()
    range_len_b = f.read(2)
    range_len = struct.unpack(">H", range_len_b)[0]
    if range_len == 0x0000:
        dprint(f"*** {f_pos:08x} EOF marker {x(range_len_b)} ***")
        return False
    elif range_len >= 0x8000:
        # copy uncompressed section
        data_len = (range_len & 0x7fff)
        if range_len == 0x8000:
            data_len = 0x8000
        dprint(f"*** {f_pos:08x} Copying uncompressed section of {data_len} bytes ***")
        data = f.read(data_len)
        window.extend(data)
        if f_out:
            f_out.write(data)
    else:
        dprint(f"*** {f_pos:08x} Decoding compressed section of {range_len} bytes ***")
        next_offset = f_pos + range_len
        out_len = 0
        while f_pos < next_offset:
            out_len += decode_block(f, f_out, next_offset - f_pos)
            f_pos = f.tell()
            if f_pos > next_offset + 2:
                raise IndexError(f"{f_pos:08x} Boom! Read {f_pos-next_offset} bytes beyond {next_offset:08x}")
        dprint(f"*** {f_pos:08x} wrote {out_len} bytes")
    return True

def decode_file(filename):
    f = open(filename, "rb")
    f.seek(args.offset)
    if args.fn_out:
        f_out = open(args.fn_out, "wb")
    else:
        f_out = None

    more_data = True
    while more_data:
        more_data = decode_range(f, f_out)

if __name__ == "__main__":
    decode_file(args.filename)
