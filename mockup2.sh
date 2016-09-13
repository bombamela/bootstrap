#! /bin/bash
for station in $(seq 2)
	do 	for cam in $(seq 10)
			do 	for zone in $(seq 2)
					do 	for try in $(seq 240)
							do 	echo "YarraTrams.Stations.Station_${station}.Camera_${cam}.Zone_${zone}.Count $((RANDOM % 100)) $((`date +%s`+$try*60-14400))" | nc -q0 0.0.0.0 2003
								echo "YarraTrams.Stations.Station_${station}.Camera_${cam}.Zone_${zone}.Demographics $((RANDOM % 100)) $((`date +%s`+$try*60-14400))" | nc -q0 0.0.0.0 2003
								for timestamp in $(seq 2)
									do 	for id in $(seq 2); do echo "YarraTrams.Stations.Station_${station}.Camera_${cam}.Zone_${zone}.Tracklets.ID_${id}.x_y_timestamp${timestamp} $((RANDOM % 100)) $((`date +%s`+$try*60-14400))" | nc -q0 0.0.0.0 2003;done
								done
						done
						echo Station_${station} Camera_${cam} Zone_${zone}
				done
		done
done

