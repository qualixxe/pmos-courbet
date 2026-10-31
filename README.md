# postmarketOS for Xiaomi Mi 11 Lite 4G (courbet)

CI builds the out-of-tree `xiaomi-courbet` port with Linux 6.13.4 and produces a
boot image plus the matching rootfs image. The port targets the Snapdragon 732G
(SM7150-AC), not SM7325.

## Why the pmaports revision is pinned

The workflow uses `kevinwidjaja21/pmaports` at commit
`9ed24e3091fe102319987aebf99c0e281ba24e19` (`courbet_stable` before its tip).
That revision contains the courbet display enablement and builds
`CONFIG_DRM_PANEL_K9A_36_02_0A=y` into the kernel.

The following commit, `e78c27e`, is explicitly named `DO NOT MERGE test packed
kernel 6.17` and disables that panel driver. Building the moving tip therefore
produces an image that can boot without any visible output. CI checks both the
revision and the panel option before starting the kernel build.

## Artifacts

Run **Build pmOS for courbet (courbet_stable fork)** from the Actions tab and
download `pmos-courbet-stable`:

- `boot-pmos-courbet.img` — kernel, courbet DTB and postmarketOS initramfs;
- `rootfs-pmos-courbet.img` — the matching root filesystem;
- `vmlinuz`, `initramfs`, `courbet.dtb` — unpacked components for inspection;
- `init.log`, `kernel.log`, `install.log` — build logs.

The boot image and rootfs must come from the same artifact: the boot command
line contains the UUID of that particular rootfs. CI verifies the match.

The image is a console installation (`ui = console`), not a graphical desktop
image.

## Before booting

The bootloader must be unlocked and the phone should run the latest stock
firmware for courbet.

**The stock DTBO must not be applied to the mainline DTB.** Erasing `dtbo` is a
requirement of this port even when using `fastboot boot`; loading boot.img over
USB does not bypass DTBO processing. Android needs the original DTBO restored
to boot again.

Back up DTBO first. Run `dd` in a rooted Android shell, then run `adb pull` on
the PC:

```sh
dd if=/dev/block/by-name/dtbo of=/sdcard/dtbo.img
```

```sh
adb pull /sdcard/dtbo.img
```

Then enter fastboot mode and erase DTBO. This changes the device and is not a
read-only test:

```powershell
$fb = "C:\Users\qualixxe\Downloads\platform-tools\fastboot.exe"
& $fb devices
& $fb erase dtbo
```

To restore the backup later:

```powershell
& $fb flash dtbo .\dtbo.img
```

## Test kernel and initramfs

After erasing DTBO, the boot image can be loaded without flashing the boot
partition:

```powershell
& $fb boot .\boot-pmos-courbet.img
```

This tests the kernel, panel, DTB, USB and initramfs. It is not a complete
installation: without the matching rootfs on `userdata`, initramfs cannot
switch to the installed system.

## Full installation

**Flashing `userdata` destroys its current contents, including Android user
data. Back up everything needed first.**

```powershell
& $fb flash userdata .\rootfs-pmos-courbet.img
& $fb boot .\boot-pmos-courbet.img
```

For a permanent installation, flash the same boot image to `boot` instead of
using `fastboot boot`. Do not mix images from different CI artifacts.

## Build details

The stable workflow installs pmbootstrap 3.4.x, checks out the pinned courbet
port, builds `linux-postmarketos-qcom-sm7150`, runs `pmbootstrap install
--no-fde`, and validates:

- Android boot-image and gzip signatures;
- the courbet DTB appended to the kernel;
- the initramfs gzip signature;
- the rootfs UUID against `pmos_root_uuid` in boot.img.

The older `build-pmos.yml` workflow is an unrelated experimental SM7150/surya
payload builder, not the supported courbet installation path.

Upstream device instructions and hardware status:
<https://wiki.nura.eco/wiki/Xiaomi_Mi_11_Lite_4G_(xiaomi-courbet)>.
