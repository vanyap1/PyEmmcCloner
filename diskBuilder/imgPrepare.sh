#!/bin/bash
# Image preparation script
# This script dumps a root filesystem image from a specified partition of a target block device.
# Flags:
# "-d <block device>"         - target block device
# "-a <filename>"             - RootFS archive filename


# This script can also resolve symlinks for the target device.
# Usege example:

# usage: ./imgPrepare.sh -d /dev/sdb -a sdhRootFs.img
# usage: ./imgPrepare.sh -d /dev/sdb -a sdhRootFs.img



EXEC_PREFIX='sudo '

ROOT_FS_IMG=""
TARGET_DEVICE=""
IMAGES_DIR="rootfsimgs"
PART_NUMBER=2

dual_part="yes"

echo "Disk image dumper..."


while [ "$#" -gt 0 ]; do
    case "$1" in

    -a)
        shift
		if [ "$#" -eq 0 ];then
			echo " <<< ERROR: Path should be provided after '-a'"
			exit 1
		fi
		ROOT_FS_IMG="${IMAGES_DIR}/$1"
		;;
    -d)
        shift
        if [ "$#" -eq 0 ];then
            echo " <<< ERROR: Path to a block device should be provided after '-d'"
            exit 1
        fi
        TARGET_DEVICE="$1"
        ;;
    
    *)
		echo " <<< ERROR: Illegal parameter '$1'"
		exit 4
		;;
    esac
    shift
done

if [ -L "${TARGET_DEVICE}" ]; then
    real_dev=$(readlink -f "${TARGET_DEVICE}")
    if [ -b "${real_dev}" ]; then
        echo "Detected that ${TARGET_DEVICE} is a symlink -> using ${real_dev}"
        TARGET_DEVICE="${real_dev}"
    else
        echo " <<< ERROR: ${TARGET_DEVICE} is a symlink, but target ${real_dev} is not a valid block device"
        exit 5
    fi
fi


echo "Running imgPrepare.sh script to prepare image file..."
echo "Target device: ${TARGET_DEVICE}"
echo "Target partition: ${TARGET_DEVICE}${PART_NUMBER}"
echo "Root FS image: ${ROOT_FS_IMG}"

# Checkink hardware dependencies before proceeding

if [ ! -b "${TARGET_DEVICE}" ];then
	echo " <<< ERROR: Wrong path to a disk device '${TARGET_DEVICE}'"
	exit 5
fi

if ! ${EXEC_PREFIX}fdisk -l "${TARGET_DEVICE}" 2>&1 | grep -q "Disk ${TARGET_DEVICE}"; then
    echo " <<< ERROR: No media found in device '${TARGET_DEVICE}' (Broken or not inserted emmc)"
    exit 8
fi

if [ ! -b "${TARGET_DEVICE}${PART_NUMBER}" ];then
	echo " <<< ERROR: Wrong path to a disk device '${TARGET_DEVICE}${PART_NUMBER}'"
	exit 5
fi

echo "Dumping image from the target device partition..."

${EXEC_PREFIX} chmod 777 "${TARGET_DEVICE}"
${EXEC_PREFIX} chmod 777 "${TARGET_DEVICE}${PART_NUMBER}"

echo "Calculating SHA256 hash of the partition..."
PART_HASH=$(${EXEC_PREFIX}sha256sum "${TARGET_DEVICE}${PART_NUMBER}" | awk '{print $1}')
echo "Partition SHA256: ${PART_HASH}"

if ! dd if="${TARGET_DEVICE}${PART_NUMBER}" of="${ROOT_FS_IMG}" bs=4M status=progress conv=fsync; then
    echo " <<< ERROR: Failed to dump image from the target device partition"
    exit 9
fi
sync
echo " <<< Image dumped successfully to '${ROOT_FS_IMG}'"
echo "Pass"
exit 0