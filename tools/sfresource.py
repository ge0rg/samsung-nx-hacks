#!/usr/bin/env python3
#
# SF_RESOURCE decoder for Samsung smart camera firmware files
#
# THIS CODE IS VERY UGLY! WASH YOUR EYES WITH SOAP, THEN DELETE FILE!

import mmap
import os
import struct
import sys
from argparse import ArgumentParser
from collections import OrderedDict
from math import ceil

P_TOP = "16s4sI8s"      # +0x0000,  32 bytes (file offsets) variable-endian
P_FILE = "56sII"        # +0x0020 + N*64, 64 bytes

MAGIC = b"SF_RESOURCE\0\0\0\0\0"

parser = ArgumentParser()
parser.add_argument('filenames', metavar='FILE.bin', nargs='+',
                    help='firmware file to analyze / extract')
parser.add_argument('-t', '--table',
                    action='store_true', dest='table', default=False,
                    help='format output as markdown table')
parser.add_argument('-x', '--extract',
                    action='store_true', dest='extract', default=False,
                    help='extract files')
args = parser.parse_args()


def read_header(f, data_offset):
    f.seek(data_offset)
    data = f.read(struct.calcsize(P_TOP))
    s = struct.Struct(P_TOP).unpack_from(data)
    return s

def dump_header(filename, f, data_offset):
    s = read_header(f, data_offset)
    if s[2] > 65535:
        # EVIL Big Endian hack: change the unpack format and re-read header
        global P_TOP, P_FILE
        P_TOP = '>' + P_TOP
        P_FILE = '>' + P_FILE
        s = read_header(f, data_offset)
    magic, version, files, padding = s
    if magic != MAGIC:
        raise ValueError("invalid SF_RESOURCE magic")
    version = version.decode('ascii')
    print(f"{filename}: SF_RESOURCE version {version} at 0x{data_offset:08x} with {files} files:\n")
    return files

def extract_file(f, fn_out, offset, size):
    print(f"Extracting from {offset:08x}: {size:8d} bytes -> {fn_out}")
    f_out = open(fn_out, "wb")
    os.sendfile(f_out.fileno(), f.fileno(), offset, size)
    f_out.close()

def dump_file(f, data_offset, dst):
    data = f.read(struct.calcsize(P_FILE))
    s = struct.Struct(P_FILE).unpack_from(data)
    fn = s[0].decode('ascii').strip('\0')
    offset = s[1]
    size = s[2]
    if args.table:
        print(f"| {fn:<30} | {offset:>9d} | {size:>9d} |")
    else:
        print(f"{fn:<30} {offset:>9d} {size:>9d}")
    if args.extract:
        extract_file(f, f"{dst}/{fn}", data_offset + offset, size)

def find_magic(f):
    with mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ) as mm:
        offset = mm.find(MAGIC, 0)
        if offset < 0:
            raise ValueError("no SF_RESOURCE magic found")
        return offset

def dump_resource(filename):
    with open(filename, "rb") as f:
        header_offset = find_magic(f)
        files = dump_header(filename, f, header_offset)
        data_offset = header_offset + 32 + 64*files
        dst = os.path.splitext(os.path.basename(filename))[0]
        if args.extract:
            os.makedirs(dst, exist_ok=True)
        for idx in range(files):
            dump_file(f, data_offset, dst)

for filename in args.filenames:
    dump_resource(filename)
