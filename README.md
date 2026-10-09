# postmarketOS payload for Xiaomi Mi 11 Lite 4G (courbet)

Builds a postmarketOS kernel + initramfs in CI and packages it as an Android
boot image that can be started with `fastboot boot`.

## Why fastboot boot

The UEFI built in `edk2-sm7150` reads **only USB Mass Storage with FAT32**:

```
MdeModulePkg/Bus/Usb/UsbMassStorageDxe   USB storage
MdeModulePkg/Universal/Disk/DiskIoDxe    block I/O
MdeModulePkg/Universal/Disk/PartitionDxe GPT/MBR
FatPkg/EnhancedFatDxe                    FAT32
```

There is no UFS driver — Qualcomm UFS is a proprietary controller that is not
on PCI, so the firmware cannot see the phone's own storage. The network stack
is compiled out as well:

```
#!include NetworkPkg/Network.fdf.inc      disabled
```

Nothing can therefore be loaded from a partition or a USB stick. That is what
blocked the earlier Windows attempt, which needed a USB-C OTG adapter that was
not available.

`fastboot boot` sidesteps it entirely: the image is pushed into RAM over USB
and started, without a partition being written. postmarketOS supports this
natively via `pmbootstrap flasher boot`, and its initramfs is self contained,
so no storage is needed at runtime either.

## Why not gitlab.postmarketos.org

It is behind **Anubis**, a proof-of-work anti-scraping gate that requires
JavaScript. Automated clients receive the challenge page instead of a git
stream, and the clone fails. That is what killed the first run of this
workflow — not a missing package.

Both dependencies are therefore sourced elsewhere:

| Need | Source |
|---|---|
| pmbootstrap | PyPI, `pip install pmbootstrap` (2.1.0) |
| pmaports | `github.com/sm7150-mainline/pmaports`, branch `generic` |

## What actually exists for this SoC

There **is** a mainline SM7150 port. In the mirror:

```
device/community/device-xiaomi-surya        device port
device/community/device-qcom-sm7150          SoC port
device/community/linux-postmarketos-qcom-sm7150   kernel package
device/community/firmware-xiaomi-surya       firmware
```

surya is a close relative of courbet: same SM7150 family, and the port even
declares the same panel.

```
deviceinfo_screen_width="1080"
deviceinfo_screen_height="2400"
deviceinfo_dtb="qcom/sm7150-xiaomi-surya-huaating"
```

But the SoC port is declared as:

```
deviceinfo_device_type="ref"
```

In postmarketOS that marks a **reference configuration kept for CI tests**, not
a device anyone has verified boots. So the honest position is:

- SM7325 mainline work is real and in progress — Nura's first announced targets
  are SM7325 devices, so the effort exists
- the SM7150 port here is a test fixture, not a working phone port
- **no `courbet` port exists**

## Why a failed boot will be silent

```
deviceinfo_getty="ttyMSM0;115200;n8"
```

The console is UART. The firmware exposes no USB while it runs, and this
phone's UART pads need a USB-TTL adapter to tap. So a kernel that starts
without a panel produces no observable output at all — neither a screen nor a
log. Expect a black screen, and expect to learn only that it got that far.

## What the workflow does

```
Resolve target        -> xiaomi-surya by default
Install deps
Install pmbootstrap   -> PyPI
Fetch pmaports        -> GitHub mirror, reports what it found
Create build user
Report maturity       -> prints the target's deviceinfo and warns when the SoC
                         port is device_type="ref"
pmbootstrap init
pmbootstrap build
Package               -> boot.img + 128 MiB padded variant
Upload
```

The maturity step exists so the "this is a reference port, not a working port"
caveat is re-read from the mirror on every run instead of going stale in a
README.

Switch target from the Actions tab (**Run workflow → `device`**).

## Using the result

```powershell
$fb = "C:\Users\qualixxe\Downloads\platform-tools\fastboot.exe"
# power off, then hold Vol Down + Power to reach fastboot
& $fb devices
& $fb boot boot-pmos.img
```

Nothing is written. If the kernel does not come up, power-cycle back into
fastboot and try the next build; `fastboot boot` leaves no trace.

## Layout

```
.github/workflows/build-pmos.yml   build in CI, package, report support status
device/courbet.deviceinfo          device definition for a future courbet port
scripts/mkbootimg.py               wrap kernel + initramfs + dtb into a boot image
```

`mkbootimg.py` writes the header itself rather than shelling out to `mkbootimg`,
and uses the Xiaomi/SM7150 convention seen in the stock image: header_version 0,
device tree appended after the ramdisk with its length at offset 1648.

## Requirements

None locally. The build needs no Linux host because CI runs it; testing needs
only `fastboot`, already present at
`C:\Users\qualixxe\Downloads\platform-tools\fastboot.exe`.
