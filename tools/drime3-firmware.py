#!/usr/bin/env python3
#
# Samsung DRIMeIII (WB850F and EX2F) firmware file decoder
#
# THIS CODE IS VERY UGLY! WASH YOUR EYES WITH SOAP, THEN DELETE FILE!

import os
import struct
import sys
from argparse import ArgumentParser


P_TOP = "<7sB"
P_PART = "<32sII20s"

parser = ArgumentParser()
parser.add_argument('filenames', metavar='FILE.bin', nargs='+',
                    help='firmware file to analyze / extract')
parser.add_argument('-x', '--extract',
                    action='store_true', dest='extract', default=False,
                    help='extract partitions')
parser.add_argument('-t', '--table',
                    action='store_true', dest='table', default=False,
                    help='format output as markdown table')
args = parser.parse_args()

def print_row(name, value):
    if args.table:
        print("| %-30s | %s |" % (name, value))
    else:
        print("%-30s %s" % (name, value))


def stringify(val):
    try:
        return '"%s"' % val.decode("ascii")
    except UnicodeDecodeError:
        try:
            return '"%s"' % bytes([b-0x80 for b in val]).decode("ascii")
        except (UnicodeDecodeError, ValueError):
            return "`"  + " ".join(f"{byte:02x}" for byte in val) + "`"

def dump_block(f, pack, names=None):
    data = f.read(struct.calcsize(pack))
    s = struct.Struct(pack).unpack_from(data)
    if names:
        for n, v in zip(names, s):
            if type(v) == int:
                print_row(n, "`0x%x` (%d)" % (v, v))
            else:
                print_row(n, stringify(v))
    else:
        print(s)
    return s

def dump_fw_info(filename):
    with open(filename, "rb") as f:
        ver, num = dump_block(f, P_TOP, ["version", "number"])
        parts = []
        for x in range(num):
            p = fn, size, offset, name = dump_block(f, P_PART, ["file_name", "size", "offset", "name"])
            parts.append(p)
        if args.extract:
            for p in parts:
                fn, size, offset, name = p
                out_fn = name.decode("ascii").strip('\0') + ".bin"
                print(f'Extracting {size} bytes at 0x{offset:x} to "{out_fn}"...')
                f_out = open(out_fn, "wb")
                os.sendfile(f_out.fileno(), f.fileno(), offset, size)
                f_out.close()


for filename in args.filenames:
    dump_fw_info(filename)

