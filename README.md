# Beacon monitoring server

This agent will run on the system controller (Lisa) 
It receives monitoring messages from the compute nodes and publishes them onto the POSIX queue.
They can be read then by any interested party running on Lisa

## Installation 
```shell script
sudo apt install python3-pip
git clone https://github.com/Ormly/ParallelNano_Lisa_Beacon_Agent.git
cd ParallelNano_Lisa_Beacon
python3 setup install --user
``` 

## Usage
```shell script
cd ParallelNano_Lisa_Beacon/beacon_server
python3 beacon_server_daemon.py
```

To kill daemon:

```shell script
$ ps -ef | grep beacon
mario       4481    1720  3 10:38 ?        00:00:00 python beacon_server_daemon.py
$ kill 4481
```

## Configuration
Agent is configured using the ```config.json``` file residing in the same library.

```json
{
  "if_ip": "127.0.0.1",
  "listen_port": 4444,
  "queue_id": "/compute_node_beacon"
}
```
* ```if_ip``` - ip of the interface to listen to
* ```listen_port``` - port to which the messages are sent form nodes
* ```queue_id``` - id of the POSIX queue to publish messages on 

**Daemon should be restarted to apply changes to config file**

## Message format on POSIX queue
The messages posted onto the POSIX queue are pickled dictionary containing the system information.
System information sent as part of the beacon is a [pickled](https://docs.python.org/3.6/library/pickle.html) dictionary with the following structure
```json
{
  "cpu":"x86_64",
  "cpu_usage":3.7,
  "hostname":"mario-virtual-machine",
  "ip_address":"127.0.1.1",
  "mem_usage":8.5540755014172,
  "platform":"Linux-5.4.0-48-generic-x86_64-with-glibc2.29",
  "system":"Linux"
} 
```

For the expected format of the pickled system information dictionary checkout [ParallelNano_Lisa_Beacon_Agent](https://github.com/Ormly/ParallelNano_Lisa_Beacon_Agent)