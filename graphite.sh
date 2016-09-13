#!/bin/bash 

docker rm -f graphite-3

docker run -d\
 --name graphite-3\
 --restart=always\
 -p 8009:80\
 -p 2003-2004:2003-2004\
 -p 2023-2024:2023-2024\
 -p 8125:8125/udp\
 -p 8126:8126\
 -v /path/to2/graphite/storage/whisper:/opt/graphite/storage/whisper \
 -v /path/to2/log:/var/log \
 hopsoft/graphite-statsd
 
sudo mkdir -p /path/to2/log/nginx
sudo mkdir -p /path/to2/log/graphite

docker restart graphite-3
sleep 1s
 
for station in $(seq 3)
	do 	for cam in $(seq 10)
			do 	for zone in $(seq 3)
					do 	for try in $(seq 3); do echo "YarraTrams.Stations.Station_${station}.Camera_${cam}.Zone_${zone}.Count $try `date +%s`" | nc -q0 0.0.0.0 2003;done
						for try in $(seq 3); do echo "YarraTrams.Stations.Station_${station}.Camera_${cam}.Zone_${zone}.Demographics $try `date +%s`" | nc -q0 0.0.0.0 2003;done
						for	id in $(seq 3)
							do 	for timestamp in $(seq 5)
									do 	for try in $(seq 3); do echo "YarraTrams.Stations.Station_${station}.Camera_${cam}.Zone_${zone}.Tracklets.ID_${id}.x_y_timestamp${timestamp} $try `date +%s`" | nc -q0 0.0.0.0 2003;done
								done
						done
						sleep 0.1s
				done
		done
done

for train in $(seq 2)
	do 	for cam in $(seq 12)
			do 	for zone in $(seq 3)
					do  for try in $(seq 3); do echo "YarraTrams.Trains.Train_${train}.Camera_${cam}.Zone_${zone}.Count $try `date +%s`" | nc -q0 0.0.0.0 2003;done
						for try in $(seq 3); do echo "YarraTrams.Trains.Train_${train}.Camera_${cam}.Zone_${zone}.Demographics $try `date +%s`" | nc -q0 0.0.0.0 2003;done
						for id in $(seq 3)
							do 	for timestamp in $(seq 5)
									do 	for try in $(seq 3); do echo "YarraTrams.Trains.Train_${train}.Camera_${cam}.Zone_${zone}.Tracklets.ID_${id}.x_y_timestamp${timestamp} $try `date +%s`" | nc -q0 0.0.0.0 2003;done
								done
						done
						sleep 0.1s
				done
		done
done
 
 