#!/usr/bin/env python3
#
# M7MU firmware update file decoder (`DATAxxxx.bin`) based on Samsung
# SM-N7505_EUR_KK_Opensource.zip
#
# Relevant structures have been taken from
# drivers/media/video/exynos/fimc-is/sensor/fimc-is-device-m7mu.h
#
# THIS CODE IS VERY UGLY! WASH YOUR EYES WITH SOAP, THEN DELETE FILE!

import struct
import sys

PRINT_TABLE = True

P_TOP = "<IIIII"            # +0x0000,  20 bytes (file offsets) little-endian
P_SDRAM = "144s"            # +0x0014, 144 bytes (array?)
P_NAND = "225s"             # +0x00A4, 225 bytes (array? contains code block size - 2)
P_CODE = "II5s12s7s13s"     # +0x01A3,  45 bytes (code size, version strings)
P_SECTION = "25I"           # +0x01D0, 100 bytes (offsets and section numbers)
P_USER_CODE = "18s18s18s"   # +0x0234,  54 bytes (memory initialization?!)

def print_row(name, value):
    if PRINT_TABLE:
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

def dump_sections(f, pack):
    data = f.read(struct.calcsize(pack))
    s = struct.Struct(pack).unpack_from(data)
    name = "section_info"
    val = "`"  + " ".join(f"{ptr:08x}" for ptr in s) + "`"
    print_row(name, val)


def dump_fw_info(filename):
    with open(filename, "rb") as f:
        dump_block(f, P_TOP, ["block_size", "writer_load_size", "write_code_entry", "sdram_param_size", "nand_param_size"])
        dump_block(f, P_SDRAM, ["sdram_data"])
        dump_block(f, P_NAND, ["nand_data"])
        dump_block(f, P_CODE, ["code_size", "offset_code", "version1", "log", "version2", "model"])
        dump_sections(f, P_SECTION)
        dump_block(f, P_USER_CODE, ["pdr", "ddr", "epcr"])


for filename in sys.argv[1:]:
    dump_fw_info(filename)
