#!/usr/bin/env python3
#
# Samsung Linux Platform (SLP) firmware header dumper for NX cameras
#
# THIS CODE IS VERY UGLY! WASH YOUR EYES WITH SOAP, THEN DELETE FILE!

import collections
import os
import struct
import sys
from argparse import ArgumentParser

# Magic header
SLP_MAGIC = b'SLP\0'

# format definition for meta and image headers
P_FWFILE_META = "<4s8s16s16sbI15s"
FwFileMeta = collections.namedtuple("FwFileMeta", "magic version project version_date has_pcache pcache_offset reserved")

P_FW_IMAGE_HEADER = "<IIII"
P_FW_IMAGE_HEADER2 = "<IIII8s"
FwImageHeader = collections.namedtuple("FwImageHeader", "img_len crc32 img_offset magic, extra filename", defaults=(None,)*6)
FW_IMAGES = ["vImage", "D4_IPL.bin", "D4_PNLBL.bin", "uImage", "platform.img"]


parser = ArgumentParser()
parser.add_argument('filenames', metavar='FILE.bin', nargs='+',
                    help='files analyze / extract')
parser.add_argument('-p', '--partitions',
                    action='store_true', dest='partitions', default=False,
                    help='print partition headers')
parser.add_argument('-x', '--extract',
                    action='store_true', dest='extract', default=False,
                    help='extract partitions into new sub-directory ./FILE/')
parser.add_argument('-o', '--output', dest='output', default=None,
                    help='extract to given directory instead of one created based on filename', metavar='DIR')
args = parser.parse_args()

def c_str(val):
    """helper to convert a byte string to human readable"""
    if not val:
        return ""
    try:
        return val.decode("ascii").strip('\0')
    except UnicodeDecodeError:
        return str(val)

def load_block(f, pack, cls, filename=None):
    """read a binary block into a named tuple"""
    data = f.read(struct.calcsize(pack))
    s = struct.unpack(pack, data)
    if filename:
        obj = cls(*s, filename=filename)
    else:
        obj = cls(*s)
    return obj

def load_image_block(f, filename="", v2=False):
    """read a partition image block"""
    return load_block(f, P_FW_IMAGE_HEADER2 if v2 else P_FW_IMAGE_HEADER, FwImageHeader, filename)

def load_v2_parts(f, count):
    """read all partition image blocks from a V2 file"""
    f.seek(struct.calcsize(P_FWFILE_META))
    parts = []
    for x in range(count):
        p = load_image_block(f, v2=True)
        parts.append(p)
    return parts

def assert_part0_magic(parts):
    """crash if the first partition's magic is wrong"""
    if parts[0].magic != 0xffffffff:
        raise Exception(f"invalid partition magic 0x{parts[0].magic:08x}, expected 0xffffffff")

def extract_files(filename, f, parts):
    """extract all partitions from a given firmware file"""
    dst = args.output
    if not dst:
        dst = os.path.splitext(os.path.basename(filename))[0]
    os.makedirs(dst, exist_ok=True)
    i = 0
    for p in parts:
        fn_out = p.filename or f"chunk-{i:02d}.bin"
        print(f"Extracting {dst}/{fn_out} ...")
        f_out = open(dst + "/" + fn_out, "wb")
        os.sendfile(f_out.fileno(), f.fileno(), p.img_offset, p.img_len)
        f_out.close()
        i = i + 1

def dump_fw_info(filename):
    """show info about firmware file on stdout"""
    with open(filename, "rb") as f:
        try:
            v2 = False
            has_pcache = False

            fw = load_block(f, P_FWFILE_META, FwFileMeta)
            if fw.magic != SLP_MAGIC:
                raise Exception(f"bad magic")
            parts = [load_image_block(f, fn) for fn in FW_IMAGES]
            assert_part0_magic(parts)
            if fw.has_pcache == 1:
                has_pcache = True
                f.seek(fw.pcache_offset)
                parts.append(load_image_block(f, "pcache.list", v2))
            if parts[1].magic != 0x7fffffff:
                parts = load_v2_parts(f, fw.has_pcache)
                assert_part0_magic(parts)
                v2 = True
        except Exception as e:
            print(f"{filename}: not an SLP firmware ({e})")
            return
        revision = f"{c_str(fw.version_date)} {c_str(fw.reserved)}".strip()
        print(f"{filename}: {c_str(fw.project)} firmware {c_str(fw.version)} ({revision}) with {len(parts)} partitions")
        if args.partitions:
            for p in parts:
                print(f"    {p.img_offset:10d} {p.img_len:10d} {p.crc32:8x} {p.magic:8x} {c_str(p.extra)} {p.filename}")
        if args.extract:
            extract_files(filename, f, parts)



for filename in args.filenames:
    dump_fw_info(filename)
