#!/usr/bin/env bash
# efi_image.sh - generate efi.bin and dtb.bin from a compiled kernel tree.
#
# Usage (called by sheepdog-slave.py --board-config):
#   bash efi_image.sh --kernel <path/to/Image> --dtb <path/to/board.dtb>
#
# Reads fixed paths for ramdisk, systemd-boot stub, and output dir from the
# directory this script lives in (the sheepdog workspace).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

KERNEL=""
DTB=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --kernel) KERNEL="$2"; shift 2 ;;
        --dtb)    DTB="$2";    shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$KERNEL" || -z "$DTB" ]]; then
    echo "Usage: $0 --kernel <Image> --dtb <board.dtb>" >&2
    exit 1
fi

RAMDISK="${SCRIPT_DIR}/ramdisk.gz"
SYSTEMD_BOOT="${SCRIPT_DIR}/efi_dir/systemd-bootaa64.efi"
STUB="${SCRIPT_DIR}/efi_dir/linuxaa64.efi.stub"
OUTPUT="${SCRIPT_DIR}/images"
CMDLINE="console=ttyMSM0,115200n8 earlycon qcom_geni_serial.con_enabled=1 qcom_scm.download_mode=1 mitigations=auto reboot=panic_warm nokaslr"

mkdir -p "${OUTPUT}"

echo "==> Generating efi.bin"
generate_boot_bins.sh efi \
    --ramdisk      "${RAMDISK}" \
    --systemd-boot "${SYSTEMD_BOOT}" \
    --stub         "${STUB}" \
    --linux        "${KERNEL}" \
    --cmdline      "${CMDLINE}" \
    --output       "${OUTPUT}"

echo "==> Generating dtb.bin"
generate_boot_bins.sh dtb \
    --input  "${DTB}" \
    --output "${OUTPUT}"

echo "==> Done. Artifacts in ${OUTPUT}"
