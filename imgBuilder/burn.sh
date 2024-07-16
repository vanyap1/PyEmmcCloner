#!/bin/bash

prog_dir=`dirname $0`

# Main disk preparation and image deployment utility
MK_DISK=${prog_dir}/mk_disk.sh

PATH_TO_EMMC_FOLDER="/media/sf_EMMC"
PATH_TO_SHARED_FOLDER="/media/sf_EMMC/ATE_FILES"
PATH_TO_LOCAL_FOLDER="/home/emmc/Documents"

PATH_TO_SHARED_TEMP_FOLDER="$PATH_TO_SHARED_FOLDER/TEMP"

VERSION=$(sed -n -e 3p $PATH_TO_SHARED_FOLDER/image_param.txt)
VERSION=${VERSION/$'\r'/}
INV_BASE=$(sed -n -e 4p $PATH_TO_SHARED_FOLDER/image_param.txt)
INV=${INV_BASE/$'\r'/}
DEVICE_ADRESS=$(sed -n -e 2p $PATH_TO_SHARED_FOLDER/image_param.txt)
DEVICE_ADRESS=${DEVICE_ADRESS/$'\r'/}
DEVICE_ADRESS=${DEVICE_ADRESS/$'2'/}
echo $DEVICE_ADRESS
EXEC_PREFIX='sudo '

PART_NO=2

SRC_DIR_INVENTORY=$PATH_TO_EMMC_FOLDER/DC_nexus

# Directory where disk partitions will be mounted
MNT_DIR=/mnt/image

# RootFS archive filename
# May be overwritten by the "-a" parameter
BRD=nxs_hc

#dev_list=/dev/sdd
dev_list=${DEVICE_ADRESS}
SRC_DIR=$PATH_TO_EMMC_FOLDER/$VERSION

#Perform usb SanDisk card reader reset
Bus=$($EXEC_PREFIX lsusb | awk '/SanDisk/ {print $2}')
Device=$($EXEC_PREFIX lsusb | awk '/SanDisk/ {print $4}')
Path="/dev/bus/usb/$Bus/$Device"
$EXEC_PREFIX /home/emmc/Documents/usbreset ${Path/:/}
sleep 4

ROOTFS_PATH=${SRC_DIR}/nxs_hc-cgl-glibc_cgl-dist.tar.bz2

INV_DIR="${SRC_DIR_INVENTORY}/${INV}"

for d in ${dev_list}; do
	echo
	echo "${cnt}: ${d}"
	${EXEC_PREFIX}fdisk -lu ${d}
	cnt=$(( ${cnt} + 1 ))
done

echo " <<< COUNT ${cnt} >>>"

echo " <<< DEV LIST ${dev_list} >>>"

for d in ${dev_list}; do
	if [ ${cnt} = 1 ]; then
		disk_dev=${d}
		break
	fi
	cnt=$(( ${cnt} - 1 ))
done


DevEmmc=$(${EXEC_PREFIX} fdisk -l | grep -o ${DEVICE_ADRESS} )
if [ -z "$DevEmmc" ]
then
	echo "Device NOT connected!"
	echo "eMMC not connected" > $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/test_fail.txt
	exit
else
	echo "Device connected"
fi

if [ -z ${INV} ];then
	${MK_DISK} -a ${ROOTFS_PATH} -d ${disk_dev}
else
	${MK_DISK} -a ${ROOTFS_PATH} -d ${disk_dev} -i ${INV_DIR}
fi

return_code=$?

if [[ ${return_code} == 0 ]]; then # Finished successfully
	echo "${MK_DISK} finished with status 0"
	echo "Pass" > $PATH_TO_LOCAL_FOLDER/wimage_pass_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/wimage_pass_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/wimage_pass.txt 
elif [[ ${return_code} == 102 ]]; then
	echo -e "\n <<< Please try again. >>>"
	echo "error unpack tar file" > $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/test_fail.txt
elif [[ ${return_code} == 103 ]]; then
	echo "error copy files inventory_dn" > $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/test_fail.txt 
elif [[ ${return_code} == 104 ]]; then
	echo -e "\n <<< Please try again. >>>"
	echo "error copy files inventory_hw" > $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/test_fail.txt 
elif [[ ${return_code} == 105 ]]; then
	echo -e "\n <<< Please try again. >>>"
	echo "error copy files inventory_pr" > $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/test_fail_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/test_fail.txt 
elif [[ ${return_code} == 107 ]]; then
	echo "error" > $PATH_TO_LOCAL_FOLDER/wimage_fail_temp.txt
	${EXEC_PREFIX} cp $PATH_TO_LOCAL_FOLDER/wimage_fail_temp.txt $PATH_TO_SHARED_TEMP_FOLDER/wimage_fail.txt 
else
	echo "exited with error code ${return_code}"
fi







