#!/bin/bash

# Flags:
# "-p"			- force the disk partitioning.
# "-1"			- partition the disk with single data partition.
# "-2"			- partition the disk with two data partitions.
# "-v"			- be more verbose
# "-d <block device>	- target block device
# "-a <filename>"	- RootFS archive filename
# "-n <part_num>"	- number of partition to populate
# "-e <filename>"	- extension script (shell script that will be sourced
#			  to perform pre- and post-processing)

#
# Configuration parameters
#

# The following line in the "/etc/sudoers" file permits the user "user_name"
# to use the "sudo" command (without password):
# user_name        ALL=(ALL)       NOPASSWD: ALL

# Updated at 25.12.17 by Yaniv Costica
# The mk_disk.sh should now be used by both RnD and production.
# In case any changes are made in this script by RnD/production, you should update production/RnD and verify that the changes are working properly at both environments.

EXEC_PREFIX='sudo '

# RootFS archive filename
ROOT_FS_ARCH=""
# Extension script
EXT_SCRIPT=""

# Directory where disk partitions will be mounted
MNT_DIR=/mnt/image

TAR_COMPRESS_FLAG=-j

PART_NO=2

dual_part="yes"

BOOTER=LOCKED #default


word_cnt ( ) {
	local cnt=0
	for w in $1; do
		cnt=$(( ${cnt} + 1 ))
	done
	echo ${cnt}
}

disk_size ( ) {
	local dev=$1
	bytes=$(${EXEC_PREFIX}fdisk -lu ${dev} | sed -ne \
		"s%Disk ${dev}: .\+, \([[:digit:]]\+\) bytes.*%\1%p")
	# Silicon Pwer 4G disk reports 7905280 sectors,
	# but fdisk allows 1 - 7905279 sector number
	echo $(( (${bytes} / 512) - 1))
}

part_size ( ) {	### called part_end in dev
	local dev=$1 part=$2
	local size=`echo $(${EXEC_PREFIX}fdisk -lu ${dev} | sed -ne \
		"s%${dev}${part}[[:space:]]\+[[:digit:]]\+[[:space:]]\+[[:digit:]]\+[[:space:]]\+\([[:digit:]]\+\)[[:space:]]\+83[[:space:]]\+Linux%\1%p")`
		### in dev:
		### "s%${dev}${part}[[:space:]]\+[[:digit:]]\+[[:space:]]\+\([[:digit:]]\+\)[[:space:]]\+[[:digit:]]\++*[[:space:]]\+83[[:space:]]\+Linux%\1%p")`
	if [ x"${size}" != x ]; then
		echo ${size}
	else
		echo 0
	fi
}


############
## ~MAIN~ ##
############

force_single_part="no"
force_dual_part="yes"


while [ "$#" -gt 0 ]; do
    case "$1" in

    -a)
		shift
		if [ "$#" -eq 0 ];then
			echo " <<< ERROR: Path should be provided after '-a'"
			exit 1
		fi
		ROOT_FS_ARCH="$1"
		;;
    -d)
		shift
		if [ "$#" -eq 0 ];then
			echo " <<< ERROR: Path to a block device should be provided after '-d'"
			exit 1
		fi
		disk_dev="$1"
		;;
    -i)	shift
		if [ "$#" -eq 0 ];then
			echo " <<< ERROR: parameter should be provided after '-e'"
			exit 1
		fi
		INV_DIR="$1"
		;;
    -s)	shift
		INV_TYPE="SAVE"
		;;
    -b)		shift
		if [ "$#" -eq 0 ]; then
			echo "Booter behvior should be provided after '-b'"
			exit 1
		fi
		BOOTER="$1"
		;;
	
    *)
		echo " <<< ERROR: Illegal parameter '$1'"
		exit 1
		;;
    esac
    shift
done



if [ ${force_single_part} = "yes" -a ${force_dual_part} = "yes" ]; then
	echo " <<< ERROR: Only one of '-1' or '-2' flags can be applied"
	exit 1
fi

if [ ${PART_NO} -ne 2 -a ${PART_NO} -ne 3 ]; then
	echo " <<< ERROR: Illegal partition number"
	exit 1
fi

# no error if existing, make parent directories as needed
${EXEC_PREFIX}mkdir -p ${MNT_DIR}

if [ ! -f ${ROOT_FS_ARCH} ]; then
	echo " <<< ERROR: Couldn't find RootFS archive - '${ROOT_FS_ARCH}'"
	exit 1
fi

if [ ! -b "${disk_dev}" ];then
	echo " <<< ERROR: Wrong path to a disk device '${disk_dev}'"
	exit 1
fi

# Make sure that we don't format the PC's HD:
disk_sectors=$(disk_size ${disk_dev})

# 1GB = 2097152 sectors
MAX_SIZE_GB=64

# Additional sanity check
if [ ${disk_sectors} -ge $(( ${MAX_SIZE_GB} * 2097152 )) ]; then
	echo "Size of the disk '${disk_dev}' exceeds ${MAX_SIZE_GB}GB - wrong device"
	exit 1
fi
###


# no error if existing, make parent directories as needed
${EXEC_PREFIX}mkdir -p ${MNT_DIR}

part_dev=${disk_dev}${PART_NO}

echo " <<< UNMOUNT ${part_dev} >>>"
${EXEC_PREFIX}umount ${part_dev}

# Reserve 16M (32768 sectors) at start of the disk
part1_sectors=32768

# 3774874 sectors ~ 1.8GB ~ 90% from 2GB
# 3355443 sectors ~ 1.6GB ~ 80% from 2GB
if [ ${force_single_part} = "yes" -o \
     ${disk_sectors} -lt 3355443 -a ${force_dual_part} = "no" ]; then
	dual_part="no"
fi



if [ ${dual_part} = "yes" ]; then
	# Then allocate two equal size partitions that occupy remaining space
	big_part_sectors=$(( (${disk_sectors} - ${part1_sectors}) / 2 ))
else
	# Then allocate a partition that occupies remaining space
	big_part_sectors=$(( (${disk_sectors} - ${part1_sectors}) ))
fi

# Partition allignments in MB

PART_ALIGN_MB=4
# Partition allignments in sectors
part_align_sec=$(( ${PART_ALIGN_MB} * 2048 ))
# Align partitions on X sectors boundary
part2_sectors=$(( ${big_part_sectors} / ${part_align_sec} * ${part_align_sec} ))

part1_end=$(( ${part1_sectors} - 1 ))
part2_end=$(( ${part1_end} + ${part2_sectors} ))
if [ ${dual_part} = "yes" ]; then
	part3_end=$(( ${part2_end} + ${part2_sectors} ))
fi


echo " <<< FDISK ${disk_dev} >>>"

echo partition 1: 1 - ${part1_end}
echo partition 2: $((${part1_end} + 1)) - ${part2_end}
if [ ${dual_part} = "yes" ]; then
	echo partition 3: $((${part2_end} + 1)) - ${part3_end}
fi

${EXEC_PREFIX}fdisk -u ${disk_dev} <<- END_FDISK
	c
	o
	n
	p
	1

	${part1_end}
	n
	p
	2

	${part2_end}
	w
END_FDISK

if [ ${dual_part} = "yes" ]; then
    #TMP_SEC=$(( $(${EXEC_PREFIX}fdisk -l | awk '/sdd2/ {print $3} ') + 1 ))
	${EXEC_PREFIX}fdisk -u ${disk_dev} <<- END_FDISK
		n
		p
		3
                $((${part2_end} + 1 ))
		${part3_end}
		w
	END_FDISK
fi

if [ ! -b ${part_dev} ]; then
	${EXEC_PREFIX}blockdev --rereadpt ${disk_dev}

	sleep 5
	echo " <<< Reread partition table >>>"
	${EXEC_PREFIX}fdisk -lu ${disk_dev}
	echo
fi

if [ ! -b ${part_dev} ]; then
	echo " <<< ERROR: block device '${part_dev}' does not exist >>>"
	echo
	exit 1
fi


if [ "${INV_TYPE}" = SAVE ]; then
	echo
	echo " <<< MOUNT ${part_dev} on ${MNT_DIR} >>>"
	${EXEC_PREFIX}mount ${part_dev} ${MNT_DIR}
	[ $? = 0 ] || { echo " <<< ERROR - MOUNT ${part_dev}"; exit 1; }

	if [ ! -b ${part_dev} ]; then
		echo " <<< ERROR: block device '${part_dev}' does not exist >>>"
		echo
		exit 1
	fi

	echo
	echo " <<< SAVE INVENTORY >>>"
	${EXEC_PREFIX}rm -f ${INV_DIR}/*.bin
	${EXEC_PREFIX}cp ${MNT_DIR}/var/local/nvram/Nexus-HW.bin ${INV_DIR}
	if [[ "$?" != 0 ]]; then
		echo "error copy files inventory_hw"
		echo -e "\n <<< Please try again. >>>"
		exit 104
	fi

	${EXEC_PREFIX}cp ${MNT_DIR}/var/local/nvram/Nexus-Production.bin ${INV_DIR}
	if [[ "$?" != 0 ]]; then
		echo "error copy files inventory_pr"
		echo -e "\n <<< Please try again. >>>"
		exit 105
	fi

	${EXEC_PREFIX}cp ${MNT_DIR}/var/local/Nexus-Dynamic.bin ${INV_DIR}
	if [[ "$?" != 0 ]]; then
		echo "error copy files inventory_dn"
		echo -e "\n <<< Please try again. >>>"
		exit 103
	fi

	echo " <<< UNMOUNT ${MNT_DIR} >>>"
	${EXEC_PREFIX}umount ${MNT_DIR}
	[[ $? = 0 ]] || { echo " <<< ERROR - UNMOUNT ${part_dev}"; \
			[[ ${ERR_STAT} = 0 ]] || exit ${ERR_STAT}; exit 15; }

fi # "${INV_TYPE}" = SAVE


echo " <<< FORMAT ${part_dev} >>>"
${EXEC_PREFIX}mkfs.ext3 -F -b 4096 ${part_dev}
[ $? = 0 ] || { echo " <<< ERROR - FORMAT ${part_dev}"; exit 1; }

echo
echo " <<< MOUNT ${part_dev} on ${MNT_DIR} >>>"
${EXEC_PREFIX}mount ${part_dev} ${MNT_DIR}
[ $? = 0 ] || { echo " <<< ERROR - MOUNT ${part_dev}"; exit 1; }

echo

################################################################################
# The following instructions are executed at the start of the "mk_disk.sh"
################################################################################



echo " <<< INSTALL ${ROOT_FS_ARCH} >>>"
${EXEC_PREFIX}tar -C ${MNT_DIR} -x ${TAR_COMPRESS_FLAG} -f ${ROOT_FS_ARCH}
ERR_STAT=$?
if [[ ${ERR_STAT} != 0 ]]; then
	echo "<<< ERROR - UNTAR ${ROOT_FS_ARCH} to ${MNT_DIR}"
	echo "error unpack tar file"
	exit 102	
fi


if [ "${BOOTER}" = "UNLOCK" ]; then
	echo " <<< UNLOCKING BOOTER  >>>"
	${EXEC_PREFIX}touch ${MNT_DIR}/etc/tech_mode_enabled
fi

################################################################################
# The following instructions are executed at the end of the "mk_disk.sh"
################################################################################
if [[ ! -z ${INV_DIR} ]]; then # Nexus
	echo
	echo " <<< COPY INVENTORY >>>"
	${EXEC_PREFIX}mkdir ${MNT_DIR}/var/local/nvram

	${EXEC_PREFIX}cp  ${INV_DIR}/Nexus-Dynamic.bin ${MNT_DIR}/var/local
	if [[ "$?" != 0 ]]; then
		echo "error copy files inventory_dn"
		echo -e "\n <<< Please try again. >>>"
		exit 103
	fi
	${EXEC_PREFIX}cp  ${INV_DIR}/Nexus-HW.bin ${MNT_DIR}/var/local/nvram
	if [[ "$?" != 0 ]]; then
		echo "error copy files inventory_hw"
		echo -e "\n <<< Please try again. >>>"
		exit 104
	fi
	${EXEC_PREFIX}cp  ${INV_DIR}/Nexus-Production.bin ${MNT_DIR}/var/local/nvram
	if [[ "$?" != 0 ]]; then
		echo "error copy files inventory_pr"
		echo -e "\n <<< Please try again. >>>"
		exit 105
	fi

	if [ "${INV_TYPE}" = SAVE ]; then
		${EXEC_PREFIX}rm -f ${INV_DIR}/*.bin
	fi # "${INV_TYPE}" = SAVE

	sleep 5
fi
echo " <<< UNMOUNT ${MNT_DIR} >>>"
${EXEC_PREFIX}umount ${MNT_DIR}
unmount_return_status=$?

# NOTE: The script will necessarily ENDS HERE since at the following condition each option provoke exit command (so don't add anything after the following condition)
if [[ "${unmount_return_status}" == 0 ]]; then 
	echo -e "\n <<< Completed! >>>"
	echo "Pass"
	exit 0
else
	echo -e "\n <<< Please try again. >>>"
	echo "error at umount with exit status ${unmount_return_status}"
	exit 107
fi


