# postmarketOS payload for Xiaomi Mi 11 Lite 4G (courbet)

Builds a postmarketOS kernel + initramfs in CI and packages it as an Android
boot image that can be started with `fastboot boot`.

## Why this path

The UEFI in `qualixxe/edk2-sm7150` reads **only USB Mass Storage with FAT32**:

```
MdeModulePkg/Bus/Usb/UsbMassStorageDxe   <- USB storage
MdeModulePkg/Universal/Disk/DiskIoDxe    <- block I/O
MdeModulePkg/Universal/Disk/PartitionDxe <- GPT/MBR
FatPkg/EnhancedFatDxe                    <- FAT32
```

There is no UFS driver, and the network stack is compiled out:

```
#!include NetworkPkg/Network.fdf.inc     <- disabled
```

Qualcomm UFS is a proprietary controller that is not on PCI, so the firmware
cannot see the phone's own storage. That rules out booting any OS from a
partition or a USB stick — which is why an earlier attempt at Windows needed a
USB-C OTG adapter that was not available.

`fastboot boot` avoids the problem entirely: it pushes an image into RAM over
USB and starts it, writing nothing to the device. postmarketOS supports this
directly through `pmbootstrap flasher boot`, and the initramfs is self
contained, so no storage is needed at runtime either.

## Honest status: there is no port for this SoC

SM7325 (Snapdragon 732G) mainline support is **in progress, not finished**.
Nura's own announced first targets are SM7325 devices, so the work exists but
has not landed.

The consequence is that this repository will happily build a kernel, and that
kernel is **expected not to reach a console on courbet**. Two gaps, in order of
severity:

1. **No mainline device tree.** The stock boot image carries courbet's Android
   device tree (398043 bytes, right after the ramdisk) and Android reports
   `ro.boot.dtb_idx=11` from the `dtbo` partition. mainline needs the same
   board in its own flatbed format; that port does not exist yet.
2. **Incomplete SoC support.** Even with a tree, `msm/sm7325` lacks finished
   support for the display pipeline, and without a panel driver there is no
   console to read.

A kernel with no working display is also hard to debug here: the UEFI does not
expose USB, and this phone's UART pads need a USB-TTL adapter to tap. So a
failed boot produces no observable output at all.

## Why the default target is not courbet

The workflow defaults to `oneplus-enchilada` (OnePlus 6, Snapdragon 845), which
is a finished mainline postmarketOS port. Building that first proves the
pipeline — pmbootstrap, kernel, initramfs, packaging — end to end, so that when
SM7325 lands the only unknown is the SoC.

Switch the target from the Actions tab (**Run workflow → `device`**) or edit the
default in `.github/workflows/build-pmos.yml`.

To try courbet specifically:

```yaml
  pmbootstrap init --work-dir work ... \
      xiaomi-courbet --kernel-flavor mainline
```

## Using the result

Download the artifact, unpack it, and start it without touching the phone:

```powershell
$fb = "C:\Users\qualixxe\Downloads\platform-tools\fastboot.exe"
# enter fastboot first: power off, hold Vol Down + Power
& $fb devices
& $fb boot boot-pmos.img
```

Nothing is written. If the kernel does not come up, power-cycle back into
fastboot and try the next build; `fastboot boot` leaves no trace.

## Layout

```
.github/workflows/build-pmos.yml   build in CI, package, report support status
device/courbet.deviceinfo          pmbootstrap device definition
scripts/mkbootimg.py               wrap kernel + initramfs + dtb into a boot image
```

`mkbootimg.py` writes the header itself rather than calling `mkbootimg`, and
uses the Xiaomi/SM7150 convention seen in the stock image: header_version 0,
the device tree appended after the ramdisk with its length recorded at offset
1648.

## Requirements

None locally. The build needs no Linux host because CI runs it; testing needs
only `fastboot`, which is already on this machine at
`C:\Users\qualixxe\Downloads\platform-tools\fastboot.exe`.
