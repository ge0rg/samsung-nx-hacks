#!/usr/bin/env python3

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
                    type=auto_int, dest='offset', default=2,
                    help='offset in input file to start decoding at')
parser.add_argument('-C', '--count',
                    type=auto_int, dest='count', default=0,
                    help='number of blocks to decompress')
parser.add_argument('-W', '--window',
                    type=auto_int, dest='window', default=8192,
                    help='window size for decompression')
parser.add_argument('-d', '--debug',
                    action='store_true', dest='debug', default=False,
                    help='emit debug output')
args = parser.parse_args()

OFS_BITS = 3
window = bytearray(b'\x00' * args.window)
window_idx = 0

block_idx = 0

def window_extend(data):
    global window, window_idx
    for d in data:
        window[window_idx] = d
        window_idx = (window_idx + 1 ) % args.window

def window_get(offset, count):
    result = bytearray()
    for i in range(count):
        result.append(window[(window_idx + args.window - offset + i) % args.window])
    return result

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

def decode_block(f, f_out=None):
    '''read a 16-bit flag from file f, read and decode the following data accordingly'''
    global block_idx
    ofs =f.tell()
    flag_bytes = f.read(2)
    flag = struct.unpack(">H", flag_bytes)[0]
    bitmask = format(flag, "016b")
    bitmask1 = bitmask + "1" # used to find() streaks of 0s
    dprint(f"{ofs:08x} ({block_idx}): bitmask {xb(flag_bytes)}")
    block_idx = block_idx + 1
    i = 0
    while i < 16:
        bit = bitmask[i]
        if bit == '0':
            # obtain number of consecutive 0 bits in flag -> number of literal bytes
            literal_len = bitmask1.find("1", i) - i
            literal = f.read(literal_len)
            dprint(f"    literal {x(literal)}")
            window_extend(literal)
            if f_out:
                f_out.write(literal)
            i += literal_len
        else:
            # read 2-byte flag and decode offset and length
            mask = f.read(2)
            ofshi_len, ofslo = struct.unpack("2B", mask)
            token_len = 3 + (ofshi_len & ((1 << OFS_BITS)-1))
            offset = ((ofshi_len >> OFS_BITS) << 8) + ofslo
            if token_len == 10:
                # variable length token with additional length byte
                vlb = f.read(1)
                mask = mask + vlb
                # the additional byte gets added to the length
                token_len = token_len + vlb[0]
                #if token_len > 128+10:
                #    raise IndexError(f"{ofs:08x}: encountered token_len = {token_len}: {x(f.read(16))}")
                if token_len == 265:
                    raise IndexError(f"{ofs:08x}: encountered token_len = {token_len}: {x(f.read(16))}")
                    #token_len = token_len + f.read(1)[0]
                    #if token_len == 255 + 265:
                    #    token_len = token_len + f.read(1)[0]
                    #    if token_len == 255 + 255 + 265:
                    #        raise IndexError(f"{ofs:08x}: encountered token_len = {token_len}: {x(f.read(16))}")
            dprint(f"    token   {xb(mask)}: {token_len} at -{offset}")
            #TODO: can we use this to validate "good" vs. bad offsets?
            if offset > len(window):
                raise IndexError(f"{ofs:08x}: trying to look back {offset} bytes in a {len(window)}-sized window")
            # extend the window byte-by-byte to prevent feeding old bytes when offset < token_len
            lookup = bytearray()
            for l in range(token_len):
                nxt = window_get(offset, 1)
                lookup.extend(nxt)
                window_extend(nxt)
            #if offset < token_len:
            #    raise IndexError(f"{ofs:08x}: trying to look back {offset} bytes for a {token_len} token")
            dprint(f"        --> {x(bytes(lookup))}")
            #dprint(f"        --> {x(bytes(lookup))} -- {x(window_get(offset, 16))}")
            if f_out:
                f_out.write(bytes(lookup))
            i += 1


f_in = open(args.filename, "rb")
f_in.seek(args.offset)
if args.fn_out:
    f_out = open(args.fn_out, "wb")
else:
    f_out = None

try:
    if args.count:
        for i in range(args.count):
            decode_block(f_in, f_out)
    else:
        while True:
            decode_block(f_in, f_out)
except struct.error:
    pass
