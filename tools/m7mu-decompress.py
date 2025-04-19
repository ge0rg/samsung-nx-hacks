#!/usr/bin/env python3

import struct
import sys
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('filename', metavar='FILE.bin',
                    help='firmware file to decompress')
parser.add_argument('-o', '--output',
                    dest='fn_out', default=False,
                    help='output file to decompress into')
parser.add_argument('-O', '--offset',
                    type=int, dest='offset', default=2,
                    help='offset in input file to start decoding at')
parser.add_argument('-d', '--debug',
                    action='store_true', dest='debug', default=False,
                    help='emit debug output')
args = parser.parse_args()

window = bytearray(b'\x00' * 8192) # TODO size
#window = bytearray() # TODO size

def x(ba):
    '''helper to output hex/readable output'''
    return ba.__repr__()

def dprint(*a):
    '''debug print'''
    if args.debug:
        print(*a)

def decode_block(f, f_out=None):
    ofs =f.tell()
    flag_bytes = f.read(2)
    flag = struct.unpack(">H", flag_bytes)[0]
    bitmask = format(flag, "016b")
    bitmask1 = bitmask + "1" # used to find() streaks of 0s
    dprint(f"{ofs:08x}: bitmask {x(flag_bytes)} {bitmask}")
    i = 0
    while i < 16:
        bit = bitmask[i]
        if bit == '0':
            literal_len = bitmask1.find("1", i) - i
            literal = f.read(literal_len)
            dprint(f"    literal {x(literal)}")
            window.extend(literal)
            if f_out:
                f_out.write(literal)
            i += literal_len
        else:
            mask = f.read(2)
            ofshi_len, ofslo = struct.unpack("2B", mask)
            token_len = 3 + (ofshi_len & 0x07)
            offset = ((ofshi_len >> 3) << 8) + ofslo
            #TODO: can we use this to validate "good" vs. bad offsets?
            #if offset > len(window):
            #    raise IndexError(f"trying to look back {offset} bytes in a {len(window)}-sized window")
            dprint(f"    token   {x(mask)} {token_len} at -{offset:x}")
            lookup = bytearray()
            lookup.extend(window[-offset:-offset+token_len])
            window.extend(lookup)
            dprint(f"        --> {x(bytes(lookup))}")
            if f_out:
                f_out.write(bytes(lookup))
            i += 1


f_in = open(args.filename, "rb")
f_in.seek(args.offset)
if args.fn_out:
    f_out = open(args.fn_out, "wb")
else:
    f_out = None

while True:
    decode_block(f_in, f_out)
