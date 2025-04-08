#!/usr/bin/env python3
#
# M7MU firmware update file decoder (`DATAxxxx.bin`) based on Samsung
# SM-N7505_EUR_KK_Opensource.zip
#
# Relevant structures have been taken from
# drivers/media/video/exynos/fimc-is/sensor/fimc-is-device-m7mu.h
#
# THIS CODE IS VERY UGLY! WASH YOUR EYES WITH SOAP, THEN DELETE FILE!

import os
import struct
import sys
from argparse import ArgumentParser
from collections import OrderedDict
from math import ceil

P_TOP = "<IIIII"            # +0x0000,  20 bytes (file offsets) little-endian
P_SDRAM = "144s"            # +0x0014, 144 bytes (array?)
P_NAND = "225s"             # +0x00A4, 225 bytes (array? contains code block size - 2)
P_CODE = "II5s12s7s13s"     # +0x01A3,  45 bytes (code size, version strings)
P_SECTION = "25I"           # +0x01D0, 100 bytes (offsets and section numbers)
P_USER_CODE = "18s18s18s"   # +0x0234,  54 bytes (memory initialization?!)

parser = ArgumentParser()
parser.add_argument('filenames', metavar='FILE.bin', nargs='+',
                    help='firmware file to analyze / extract')
parser.add_argument('-p', '--partitions',
                    action='store_true', dest='partitions', default=False,
                    help='print detailed partition information')
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

def dump_block(f, pack, names=None, infostore=None):
    data = f.read(struct.calcsize(pack))
    s = struct.Struct(pack).unpack_from(data)
    if names:
        for n, v in zip(names, s):
            if type(v) == int:
                print_row(n, "`0x%x` (%d)" % (v, v))
            else:
                print_row(n, stringify(v))
            if infostore is not None:
                infostore[n] = v
    else:
        print(s)

def dump_section_info(f, pack, infostore):
    data = f.read(struct.calcsize(pack))
    s = struct.Struct(pack).unpack_from(data)
    name = "section_info"
    count = s[0]
    numbers = s[1:1+2*count:2]
    lengths = s[2:1+2*count:2]
    val = "`"  + " ".join(f"{n}:{l:08x}" for n, l in zip(numbers, lengths)) + "`"
    print_row(name, val)
    if infostore is not None:
        infostore[name] = s

def dump_partitions(info, total_size):
    partitions = []
    partitions.append(("boot", info['block_size'], info['writer_load_size']))
    block_size = 0x200 #info['block_size']
    count = info['section_info'][0]
    numbers = info['section_info'][1:1+2*count:2]
    lengths = info['section_info'][2:1+2*count:2]
    offset = info['offset_code']
    for i, l in zip(numbers, lengths):
        partitions.append((f"chunk-{i:02d}", offset, l))
        offset += ceil(l / block_size) * block_size
    partitions.append(("sf_resource", offset, total_size-offset))
    if args.partitions:
        print(f"\n{len(partitions)} partitions, ~ {sum(lengths)}/{info['code_size']} bytes:\n")
        for p in partitions:
            if args.table:
                print(f"| {p[1]:08x} | {p[2]:9d} | {p[0]} |")
            else:
                print(f"{p[1]:08x} {p[2]:9d} {p[0]}")
    return partitions

def extract_file(f, fn_out, offset, size):
    print(f"Extracting from {offset:08x}: {size:8d} bytes -> {fn_out}")
    f_out = open(fn_out, "wb")
    os.sendfile(f_out.fileno(), f.fileno(), offset, size)
    f_out.close()

def extract_files(f, filename, partitions):
    dst = os.path.splitext(os.path.basename(filename))[0]
    os.makedirs(dst, exist_ok=True)
    for fn, offset, size in partitions:
        extract_file(f, f"{dst}/{fn}.bin", offset, size)

def dump_fw_info(filename):
    with open(filename, "rb") as f:
        info = OrderedDict()
        dump_block(f, P_TOP, ["block_size", "writer_load_size", "write_code_entry", "sdram_param_size", "nand_param_size"], info)
        dump_block(f, P_SDRAM, ["sdram_data"], info)
        dump_block(f, P_NAND, ["nand_data"], info)
        dump_block(f, P_CODE, ["code_size", "offset_code", "version1", "log", "version2", "model"], info)
        dump_section_info(f, P_SECTION, info)
        dump_block(f, P_USER_CODE, ["pdr", "ddr", "epcr"], info)
        p = dump_partitions(info, os.fstat(f.fileno()).st_size)
        if args.extract:
            extract_files(f, filename, p)

for filename in args.filenames:
    dump_fw_info(filename)
