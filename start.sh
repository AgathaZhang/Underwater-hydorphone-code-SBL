#!/bin/sh

sleep 10

curTime=$(date)
echo "[$curTime] start." >> /home/pi/NeptunePi/start_log.txt

sleep 10

cd /home/pi/RaspberryPi_4chRecDriver
./load.sh tlv320adcx120
echo "[${curTime}] start load ok." >> /home/pi/NeptunePi/start_log.txt

sleep 10

cd /home/pi/NeptunePi
nohup python3 /home/pi/NeptunePi/neptune.py &
echo "[${curTime}] start python ok." >> /home/pi/NeptunePi/start_log.txt

echo "" >> /home/pi/NeptunePi/start_log.txt

