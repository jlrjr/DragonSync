# Things to consider
* add logging - run as new process `python utils/zmq_logger_for_kml.py --zmq-port 4224 --output-csv drone_log.csv`, then checkout generate_kml.py for visualizing tracks
* add health data to system
* add track heading and speed for drone
* entity grouping for drone, pilot, home
* add signal frequency based on sdr selection
* add range rings around pilot location for common ranges
* map symbololgy sidc based on tak symbol
* add payloads for system components?
* drone, pilot, home `relationship...tracked by` link to system
* `createdTime` based on first seen if possible
