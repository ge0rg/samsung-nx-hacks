#!/bin/sh

FN=/mnt/mmc/autoexec.log

run() {
	echo -e "\n----> $@" >> $FN
	"$@" >> $FN 2>&1
	echo "" >> $FN
}

run date
run id
run echo "$PATH"
run ps axfu
run mount

run cat /etc/passwd

mkdir -p /dev/pts
mount -t devpts none /dev/pts

# launch ftpd for SD card and telnet without password
inetd /mnt/mmc/inetd.conf

(sleep 30; netstat -npa >> $FN ) &
