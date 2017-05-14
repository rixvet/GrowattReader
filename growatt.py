#!/usr/bin/env python
import csv
import os
import serial
import time

ser = serial.Serial('/dev/ttyUSB1', 9600, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=5)

# Request interval data at 1500ms each
values = bytearray([0x3F, 0x23, 0x7E, 0x34, 0x41, 0x7E, 0x32, 0x59, 0x31, 0x35, 0x30, 0x30, 0x23, 0x3F])
ser.write(values)
# Dummy read to confirm retrival
ser.read(10)

# Request interval data
values = bytearray([0x3F, 0x23, 0x7E, 0x34, 0x42, 0x7E, 0x23, 0x3F])
ser.write(values)


# Start retrieving data, in a buffered way. Ones one line is detected (starting
# with 0x57 and length 31 bytes) it will be parsed
buf = bytearray([])
prev_time = 0
while True:
    values = ser.read(10)
    b = bytearray(values)
    buf = buf + b
    if 0x57 in buf:
        index = map(lambda x: x == 0x57, buf).index(True)
	if (len(buf) - index) > 32:
		# Slide to correct window
		drop = buf[:index]
        	result = buf[index:index+31]
        	buf = buf[index+31:]

		# Only log every 5 Seconds
		if time.time() < prev_time + 5:
			continue
		else:
			prev_time = time.time()

		# Make mapping and translation easy
		d = map(int, result)

		# Retrieve all values
		h = {}
		h['pv1_voltage']       = float((d[ 1] << 8) + d[ 2]) / 10
		#h['dont_care']         = float((d[ 3] << 8) + d[ 4]) / 10
		h['pv2_voltage']       = float((d[ 5] << 8) + d[ 6]) / 10
		h['grid_voltage']      = float((d[ 7] << 8) + d[ 8]) / 10
		h['grid_freq']         = float((d[ 9] << 8) + d[10]) / 100
		h['output_power']      = float((d[11] << 8) + d[12]) / 10
		h['temperature']       = float((d[13] << 8) + d[14]) / 10
		h['inverter_status']   = d[15]
		h['inverter_fault']    = d[16]
		#h['dont_care2']        = float((d[17] << 8) + d[18]) / 10
		#h['dont_care3']        = float((d[19] << 8) + d[20]) / 10
		h['energy_today']      = float((d[21] << 8) + d[22]) / 10
		h['energy_total']      = float((d[23] << 24) + (d[24] << 16) + (d[25] << 8) + d[26]) / 10
		h['total_time_worked'] = float((d[27] << 24) + (d[28] << 16) + (d[29] << 8) + d[30]) / 10
		h['time'] = time.time()
		h['raw'] = str(result).encode('base64').replace('\n','')

		# Store data into CSV file
  		csvfile = time.strftime("/home/pi/GROWATT_DATA_%Y_%m.csv")
  		with open(csvfile, "a") as output:
      			writer = csv.DictWriter(output, fieldnames=sorted(h.keys()), 
                    				delimiter=";", lineterminator='\n')
			# New file => new header
			if output.tell() == 0:
				writer.writeheader()
      			writer.writerow(h)
		
		


