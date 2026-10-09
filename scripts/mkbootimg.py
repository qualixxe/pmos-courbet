#!/usr/bin/env python3
"""
Wrap a postmarketOS kernel + initramfs into an Android boot image so it can be
started with `fastboot boot`.

This is the delivery path that matters here. The firmware built in this project
has no UFS driver and no network stack, so nothing can be loaded from storage -
but `fastboot boot` pushes an image straight into RAM over USB and starts it,
which needs no medium at all and writes nothing to the device.

Layout produced, matching what the courbet bootloader accepts:

    header_version 0, page 4096
    kernel  = <kernel image, uncompressed>
    ramdisk = <gzip of the initramfs cpio>
    dtb     = appended after the ramdisk, with its length recorded at offset
              1648, which is the Xiaomi/SM7150 convention seen in the stock
              boot image

    usage: mkbootimg.py --kernel vmlinuz --ramdisk initramfs --dtb courbet.dtb -o boot.img
"""

import argparse
import gzip
import hashlib
import struct
import sys
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
PAGE_SIZE = 4096
KERNEL_ADDR = 0x8000
RAMDISK_ADDR = 0x1000000
TAGS_ADDR = 0x100
OS_VERSION = 0x16000174
BOOT_PARTITION_SIZE = 0x8000000

# Xiaomi/SM7150 places the DTB after the ramdisk and stores its length at 1648.
OFF_XIAOMI_HEADER_SIZE = 1644
OFF_XIAOMI_DTB_SIZE = 1648


def align_up(v, p):
    return (v + p - 1) // p * p


def build(kernel: bytes, ramdisk: bytes, dtb: bytes | None) -> bytes:
    header = bytearray(PAGE_SIZE)
    header[0:8] = BOOT_MAGIC
    struct.pack_into("<I", header, 8, len(kernel))
    struct.pack_into("<I", header, 12, KERNEL_ADDR)
    struct.pack_into("<I", header, 16, len(ramdisk))
    struct.pack_into("<I", header, 20, RAMDISK_ADDR)
    struct.pack_into("<I", header, 24, 0)
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I", header, 32, TAGS_ADDR)
    struct.pack_into("<I", header, 36, PAGE_SIZE)
    struct.pack_into("<I", header, 40, 0)
    struct.pack_into("<I", header, 44, OS_VERSION)
    if dtb:
        struct.pack_into("<I", header, OFF_XIAOMI_HEADER_SIZE, 1660)
        struct.pack_into("<I", header, OFF_XIAOMI_DTB_SIZE, len(dtb))
    digest = hashlib.sha1()
    for blob in (kernel, ramdisk, dtb or b""):
        digest.update(blob)
        digest.update(struct.pack("<I", len(blob)))
    header[576:596] = digest.digest()

    out = bytearray(header)
    for blob in (kernel, ramdisk, dtb or b""):
        if not blob:
            continue
        out += blob
        out += b"\x00" * (align_up(len(out), PAGE_SIZE) - len(out))
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kernel", required=True)
    ap.add_argument("--ramdisk", required=True)
    ap.add_argument("--dtb")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--pad-to-partition", action="store_true")
    args = ap.parse_args()

    kernel = Path(args.kernel).read_bytes()
    ramdisk = Path(args.ramdisk).read_bytes()
    # postmarketOS exports an already gzipped initramfs; the bootloader expects
    # the ramdisk slot to be a gzip stream, so only compress when it is not one.
    if ramdisk[:2] != b"\x1f\x8b":
        ramdisk = gzip.compress(ramdisk, compresslevel=6, mtime=0)
    else:
        # Re-pack so the stream is well formed even if pmbootstrap used a tool
        # that produced a multi-member stream.
        try:
            ramdisk = gzip.compress(gzip.decompress(ramdisk), compresslevel=6, mtime=0)
        except OSError:
            pass

    dtb = None
    if args.dtb:
        dtb = Path(args.dtb).read_bytes()
        if dtb[:4] != FDT_MAGIC:
            print("FAIL: %s is not a device tree (magic %s)" % (args.dtb, dtb[:4].hex()),
                  file=sys.stderr)
            return 1
        total = int.from_bytes(dtb[4:8], "big")
        if total != len(dtb):
            print("FAIL: FDT totalsize %d != file size %d" % (total, len(dtb)), file=sys.stderr)
            return 1

    image = build(kernel, ramdisk, dtb)
    if len(image) > BOOT_PARTITION_SIZE:
        print("FAIL: image exceeds the boot partition", file=sys.stderr)
        return 1
    if args.pad_to_partition:
        image += b"\x00" * (BOOT_PARTITION_SIZE - len(image))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_bytes(image)

    print("kernel  : %d bytes" % len(kernel))
    print("ramdisk : %d bytes (gzip)" % len(ramdisk))
    print("dtb     : %s" % (f"{len(dtb)} bytes" if dtb else "none"))
    print("out     : %s (%d bytes, %.2f MiB)"
          % (args.out, len(image), len(image) / 1048576))
    print()
    print("Test it with: fastboot boot %s" % Path(args.out).name)
    print("Nothing is written to the device.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
