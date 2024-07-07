# Device Permission Script and GUI Autostart Service Configuration

This repository contains a guide for configuring UDEV rules to set device permissions and create a systemd service to automatically start a GUI script after the graphical environment and network are initialized, with an additional delay of 40 seconds.

## UDEV Rules Configuration

### Step 1: Identify Device ID_PATH

Run the following command to get the `ID_PATH` of your interested device:

```bash
udevadm info --query=all --name=/dev/sdX

Example output:
sdm - platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.4:1.0-scsi-0:0:0:2
sdj - platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.3:1.0-scsi-0:0:0:2
sdg - platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.2:1.0-scsi-0:0:0:2
sdd - platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.1:1.0-scsi-0:0:0:2


Step 2: Create Permission Script
Create a script to change device permissions:

sudo nano /usr/local/bin/set_permissions.sh

Add the following content to the script:

#!/bin/bash
chmod 777 /dev/$1
if [ -L /dev/$1 ]; then
    target=$(readlink -f /dev/$1)
    chmod 777 "$target"
fi

Save and make the script executable:

sudo chmod +x /usr/local/bin/set_permissions.sh

Step 3: Create UDEV Rule
Create a new UDEV rule file:

sudo nano /etc/udev/rules.d/99-usb-disk.rules

Add the following content to the file, modifying ENV{ID_PATH} and SYMLINK as needed:

SUBSYSTEM=="block", KERNEL=="sd*", ENV{ID_PATH}=="platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.4:1.0-scsi-0:0:0:2", SYMLINK+="mmca", MODE="0777"
SUBSYSTEM=="block", KERNEL=="sd*", ENV{ID_PATH}=="platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.3:1.0-scsi-0:0:0:2", SYMLINK+="mmcb", MODE="0777"
SUBSYSTEM=="block", KERNEL=="sd*", ENV{ID_PATH}=="platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.2:1.0-scsi-0:0:0:2", SYMLINK+="mmcc", MODE="0777"
SUBSYSTEM=="block", KERNEL=="sd*", ENV{ID_PATH}=="platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.3.1:1.0-scsi-0:0:0:2", SYMLINK+="mmcd", MODE="0777"

Save the file and reload UDEV rules:

sudo udevadm control --reload-rules
sudo udevadm trigger

Reboot the system to apply the changes and check the devices.

GUI Autostart Service Configuration
Step 1: Create systemd Service File
Create a systemd service file:

sudo nano /etc/systemd/system/gui.service

[Unit]
Description=Run GUI after graphical environment, network, and additional 40 seconds delay
After=graphical.target network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 40
ExecStart=/usr/bin/python3 /home/pi/gui/main.py
Restart=always

[Install]
WantedBy=graphical.target

Save the file and reload systemd:

sudo systemctl daemon-reload

Step 2: Enable and Start the Service
Enable the service to start at boot:

sudo systemctl enable gui.service

Start the service immediately:

sudo systemctl start gui.service

Step 3: Check Service Status
Check the status of the service to ensure it is running:

sudo systemctl status gui.service
