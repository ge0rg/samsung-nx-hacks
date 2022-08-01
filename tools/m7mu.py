# M7MU firmware update file decoder (`DATAxxxx.bin`) based on Samsung
# SM-N7505_EUR_KK_Opensource.zip
#
# Relevant structures have been taken from
# drivers/media/video/exynos/fimc-is/sensor/fimc-is-device-m7mu.h
#
# THIS CODE IS VERY UGLY! WASH YOUR EYES WITH SOAP, THEN DELETE FILE!

import struct
import sys

P_TOP = "<IIIII"
P_SDRAM = "144s"
P_NAND = "225s"
P_CODE = "II5s12s7s13s"
P_SECTION = "100s"
P_USER_CODE = "18s18s18s"

def dump_block(f, pack, names=None):
    data = f.read(struct.calcsize(pack))
    s = struct.Struct(pack).unpack_from(data)
    if names:
        for n, v in zip(names, s):
            if type(v) == int:
                print("%-30s 0x%x (%d)" % (n, v, v))
            else:
                print("%-30s %s" % (n, v))
    else:
        print(s)


def dump_fw_info(filename):
    with open(filename, "rb") as f:
        dump_block(f, P_TOP, ["block_size", "writer_load_size", "write_code_entry", "sdram_param_size", "nand_param_size"])
        dump_block(f, P_SDRAM, "sdram_data")
        dump_block(f, P_NAND, "nand_data")
        dump_block(f, P_CODE, ["code_size", "offset_code", "version1", "log", "version2", "model"])
        dump_block(f, P_SECTION, ["section_info"])
        dump_block(f, P_USER_CODE, ["pdr", "ddr", "epcr"])


for filename in sys.argv[1:]:
    dump_fw_info(filename)
