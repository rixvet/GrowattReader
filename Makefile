all: update parse graph

update:
	rsync -av 'homepi:~/GROWATT_DATA_20*_*.csv' .
parse:
	./growatt.py parse ./GROWATT_DATA_$$(date -d '1 month ago' '+%Y_%m').csv \
	./GROWATT_DATA_$$(date '+%Y_%m').csv > values.csv

graph:
	kst2 ./growatt.kst

