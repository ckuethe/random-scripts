#!/bin/sh

# I typically use these VMs on an external disk with lots of disk
# space. This is useful in snapshot mode which redirects writes to
# some staging space and which might fill up your home directory
# or /tmp
export TMPDIR=$(dirname $(realpath $0 ))
export SDL_VIDEO_WINDOW_POS=0,0

VMDISK=vm_image.qcow2
RAM=4096
NCPU=2
# CDBOOT="-boot d -cdrom boot_cd.iso"


${SUDO} \
qemu-system-x86_64\
	-enable-kvm \
	-cpu host \
	-machine q35,accel=kvm \
	-smp $NCPU \
	-vga virtio \
	-usb -device usb-ehci,id=ehci -device usb-tablet,bus=usb-bus.0
	-localtime \
	-m $RAM \
	-sandbox on \
	-display sdl \
	-device e1000,netdev=mynet0 -netdev type=user,id=mynet0 \
	-monitor stdio \
	$CDBOOT $VMDISK

