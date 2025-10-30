```shell
python record_joint_positions.py
python playback_recorded_positions.py --base-url http://localhost:80 --robot-id 0 --positions recorded_positions.json --duration 2.0 --steps 30 --letter-pause 0.6
python oracle_robot_server.py
python server.py
```
