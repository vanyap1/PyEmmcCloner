#!/bin/bash

# Disk preparation script
# This script prepares a disk for use by creating partitions and copying a root filesystem image to it.
# Flags:
# "-p <partitioning_scheme>" - partitioning scheme: "single" for single data partition, "dual" for two data partitions.
# "-d <block device>"         - target block device
# "-a <filename>"             - RootFS archive filename

# usage: ./diskPrepare.sh -d /dev/sdb -a sdhRootFs.img -p dual

# checking partitioning scheme - fdisk -l /dev/sdX

#export LC_ALL=en_US.UTF-8
#export LANG=en_US.UTF-8


EXEC_PREFIX='sudo '

ROOT_FS_IMG=""
TARGET_DEVICE=""
IMAGES_DIR="rootfsimgs"

dual_part="yes"

echo "Preparing disk..."


disk_size ( ) {
	local dev=$1
	bytes=$(${EXEC_PREFIX}fdisk -lu ${dev} | sed -ne \
		"s%Disk ${dev}: .\+, \([[:digit:]]\+\) bytes.*%\1%p")
	echo $(( (${bytes} / 512) - 1))
}

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
    -p)
        shift
        if [ "$#" -eq 0 ];then
            echo " <<< ERROR: Partitioning scheme should be provided after '-p'"
            exit 2
        fi
        PART_SCHEME="$1"
        if [ "${PART_SCHEME}" = "single" ]; then
            dual_part="no"
        elif [ "${PART_SCHEME}" = "dual" ]; then
            dual_part="yes"
        else
            echo " <<< ERROR: Unknown partitioning scheme '${PART_SCHEME}'"
            exit 3
        fi
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

if [ ! -b "${TARGET_DEVICE}" ];then
	echo " <<< ERROR: Wrong path to a disk device '${TARGET_DEVICE}'"
	exit 5
fi

if ! ${EXEC_PREFIX}fdisk -l "${TARGET_DEVICE}" 2>&1 | grep -q "Disk ${TARGET_DEVICE}"; then
    echo " <<< ERROR: No media found in device '${TARGET_DEVICE}' (Broken or not inserted emmc)"
    exit 8
fi

device_size=$(${EXEC_PREFIX}blockdev --getsize64 "${TARGET_DEVICE}" 2>/dev/null || echo "0")
if [ "${device_size}" -eq 0 ]; then
    echo " <<< ERROR: Device '${TARGET_DEVICE}' has zero size (no media inserted)"
    exit 8
fi

if [ ! -f ${ROOT_FS_IMG} ]; then
	echo " <<< ERROR: Couldn't find RootFS archive - '${ROOT_FS_IMG}'"
	exit 6
fi

echo "Disk device to prepare: $TARGET_DEVICE"
echo "Root FS architecture: $ROOT_FS_IMG"


disk_sectors=$(disk_size ${TARGET_DEVICE})
echo "Disk sectors: ${disk_sectors}"

# Reserve 16M (32768 sectors) at start of the disk
part1_sectors=32768
part1_end=$(( ${part1_sectors} - 1 ))

# Calculating partition 2 size and end sector
img_size=$(stat -c%s "${ROOT_FS_IMG}")
sector_size=512
part2_sectors=$(( (${img_size} + ${sector_size} - 1) / ${sector_size} ))

# Calculating partition 3 start and end sector
if [ ${dual_part} = "yes" ]; then
    part2_end=$(( ${part1_end} + ${part2_sectors} ))
    part3_end=$(( ${disk_sectors} - 1 ))
	echo "Partition 3 starts at sector $(( ${part2_end} + 1 )) and ends at sector ${part3_end}"
fi

echo "Creating partition table on $TARGET_DEVICE ..."
echo "Partition 1: end=${part1_end}"
echo "Partition 2: start=$(( ${part1_end} + 1 )), end=$(( ${part1_end} + ${part2_sectors} )), size=${part2_sectors} sectors"

if [ ${dual_part} = "yes" ]; then
    echo "Partition 3: start=$(( ${part2_end}))"
fi
${EXEC_PREFIX}fdisk -u ${TARGET_DEVICE} <<- END_FDISK
	c
	o
	n
	p
	1

	${part1_end}
	n
	p
	2
	$(( ${part1_end} + 1 ))
    $(( ${part1_end} + ${part2_sectors} ))
	w
END_FDISK

if [ ${dual_part} = "yes" ]; then
	${EXEC_PREFIX}fdisk -u ${TARGET_DEVICE} <<- END_FDISK
		n
		p
		3

        ${part3_end}
		w
	END_FDISK
fi

# Reference partition table layout:
# Device     Boot   Start      End Sectors  Size Id Type
# /dev/sdh1            62    32767   32706   16M 83 Linux
# /dev/sdh2         32768  5111807 5079040  2.4G 83 Linux
# /dev/sdh3       5111808 10190847 5079040  2.4G 83 Linux (unused partition)

echo "Writing RootFS image..."


${EXEC_PREFIX} chmod 777 "${TARGET_DEVICE}" 

if ! dd if=${ROOT_FS_IMG} of=${TARGET_DEVICE} bs=16M \
      oflag=seek_bytes seek=$(((${part1_end} + 1) * ${sector_size})) \
      conv=notrunc,sync status=progress; then
    echo " <<< ERROR: Failed to write RootFS image to disk"
    exit 7
fi

sync
echo " <<< Disk preparation completed successfully >>>"
echo "Pass"
exit 0