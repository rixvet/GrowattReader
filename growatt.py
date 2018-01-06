#!/usr/bin/env python
#
# Read Growatt 1500 usage data and store in CSV file for further processing
#
# Rick van der Zwet <info@rickvanderzwet.nl>
#
import csv
import os
import serial
import sys
import time


def request_start(ser):
	while True:
		# Request interval data at 1500ms each
		values = bytearray([0x3F, 0x23, 0x7E, 0x34, 0x41, 0x7E, 0x32, 0x59, 0x31, 0x35, 0x30, 0x30, 0x23, 0x3F])
		ser.write(values)

		# Dummy read to confirm retrival of data and alive checking
		values = ser.read(5)
		if len(values) == 5:
			break
		else:
			# Try again after a while
			time.sleep(60)
	

	# Request interval data
	values = bytearray([0x3F, 0x23, 0x7E, 0x34, 0x42, 0x7E, 0x23, 0x3F])
	ser.write(values)


def receive_data(ser):
	# Start retrieving data, in a buffered way. Ones one line is detected (starting
	# with 0x57 and length 31 bytes) it will be parsed
	buf = bytearray([])
	prev_time = 0
	while True:
	    # When inverter is no longer responding assume sunset and wait for next day
	    values = ser.read(10)
	    if len(values) < 10:
		break
	
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
	
			# Retrieve all values stored in the byte-array
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
			

def parse(csvfile, header=False):
    """ Output seems to have no CRC causing invalid entries to be logged"""

    with open(csvfile, 'rb') as fh:
        # Ensure \0 values (read errors) are filtered out before start
        reader = csv.DictReader([row for row in fh if not '\0' in row], delimiter=';', lineterminator='\n')
        if header:
            # Only print header ones (during start)
            print ';'.join(sorted(reader.fieldnames))
    
        prev_row = {'energy_today': 0, 'time' : 0}
        for row in reader:
            # Discard read errrors found using various outliar detections
            if not row['inverter_status'] in ('0', '1'):
                continue
            if not row['inverter_fault'] in ('0', '1'):
                continue
            if float(row['temperature']) > 40 or float(row['temperature']) <= 10:
                # Seems inverter temperature which is located inside
                continue
            if float(row['total_time_worked']) > (20 * 365 * 24 * 60):
                # No panels older than 20 years continous operations
                continue
            if float(row['total_time_worked']) == 0:
                # No panels with zero seconds on the clock
                continue
            if float(row['output_power']) > 2000:
                # Have 6 * 280Wp maximum available
                continue
            if float(row['energy_total']) > 20 * (6 * 280):
                # We could never produce more than our maximum capacity
                continue
            if float(row['pv2_voltage']) > 500:
                # Maximum PV voltage cannot be exceded
                continue
            if (float(row['time']) - float(prev_row['time'])) < 100:
                if (float(row['energy_today']) - float(prev_row['energy_today'])) > 1.0:
                # Check only allowed on small time delta's
                    # No large delta posible in production as intervals are short
                    continue
            if float(row['grid_freq']) > 100 or float(row['grid_voltage']) > 500:
                # Let's seriously hope there are measurement errors, else I
                # have to have a strong chat with my elektricitiy distributor
                continue

            print ';'.join([row[x] for x in sorted(reader.fieldnames)])
            prev_row = row
            
    
	

#
# Main runner
if __name__ == '__main__':
        if sys.argv[1] == 'parse':
            for i, csvfile in enumerate(sys.argv[2:]):
                parse(csvfile, i == 0)
        else:
	    ser = serial.Serial('/dev/ttyUSB1', 9600, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=5)
	    while True:
                    # Initialize Growatt, asking it to sent usage data
	    	request_start(ser)
                    # Start receiving usage data
	    	receive_data(ser)
