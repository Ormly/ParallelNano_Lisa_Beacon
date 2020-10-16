#
# THU - Team Oriented Project - WS20/21
#
"""
The server component of the beacon monitoring system
"""
from typing import Tuple, Dict, Any
import socket
import json
import sys
import os
import signal
import pickle

from ipcqueue import posixmq
import daemon


class ConfigFileInvalidError(Exception):
    """
    Should be raised to indicate an invalid config file structure
    """
    pass


class BeaconServer:
    """
    Listens to the configured port on the configured interface and puts incoming sys info
    messages onto the IPC queue
    """
    DEFAULT_BUFFER_SIZE = 2048

    def __init__(self, ip_port: Tuple[str, int], queue_id: str, queue_size: int):
        self.ip_port = ip_port
        self.queue_id = queue_id
        self.queue_size = queue_size

        self.sock: socket.socket
        self.ipc_queue: posixmq.Queue

        self._init_queue()
        self._init_and_bind_socket()

    def _init_and_bind_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.ip_port)

    def _init_queue(self):
        if not (isinstance(self.queue_id, str) and self.queue_id.startswith("/") and len(self.queue_id) < 255):
            raise ValueError("Invalid queue id")
        self.ipc_queue = posixmq.Queue(name=self.queue_id)

    def start(self):
        """
        Poll UDP socket and post incoming messages of the IPC queue
        If full, keep polling socket but do nothing else
        :return:
        """
        while True:
            msg, (ip, _) = self.sock.recvfrom(self.DEFAULT_BUFFER_SIZE)
            msg_dict = self._inject_ip_addr_to_dict(msg, ip)
            try:
                self.ipc_queue.put_nowait(msg_dict)
            except posixmq.queue.Full:
                # queue is full -> nobody's listening on the other side. nothing to do.
                pass

    def cleanup(self):
        """
        clean up any open resources (queue and socket)
        :return:
        """
        if self.sock:
            self.sock.close()

        if self.ipc_queue:
            self.ipc_queue.close()

    @staticmethod
    def _inject_ip_addr_to_dict(msg: bytes, ip: str) -> Dict[Any, Any]:
        """
        Unpickle dict, inject ip address, return
        """
        sys_info_dict = pickle.loads(msg)
        sys_info_dict["ip_address"] = ip
        return sys_info_dict


class ServerFactory:
    """
    Creates a BeaconServer from a validated config file
    """
    def from_config_file(self, filepath: str) -> BeaconServer:
        with open(filepath, 'r') as f:
            config = json.load(f)
            self._validate_config_file(config)
            ip = config['if_ip']
            port = config['listen_port']
            queue_id = config['queue_id']
            queue_size = config['queue_size']

            return BeaconServer(ip_port=(ip, port), queue_id=queue_id, queue_size=queue_size)

    @staticmethod
    def _validate_config_file(config: Dict):
        """
        check that config file contains all mandatory fields and raise a ConfigFileInvalidError if not
        :param config:
        :return:
        """
        if not isinstance(config, dict):
            raise ConfigFileInvalidError("Config file is not a valid dictionary")
        if "if_ip" not in config.keys():
            raise ConfigFileInvalidError("if_ip missing in config file")
        if "listen_port" not in config.keys():
            raise ConfigFileInvalidError("listen_port missing in config file")
        if "queue_id" not in config.keys():
            raise ConfigFileInvalidError("queue_id missing in config file")
        if "queue_size" not in config.keys():
            raise ConfigFileInvalidError("queue_size missing in config file")


def main(daemon_context: daemon.DaemonContext):
    factory = ServerFactory()
    server = factory.from_config_file("config.json")

    # set termination callback
    daemon_context.signal_map[signal.SIGTERM] = server.cleanup
    server.start()


if __name__ == '__main__':
    # TODO: optionally get config file path from stdin
    config_file = open("config.json", 'r')

    with daemon.DaemonContext(
        files_preserve=[config_file],
        chroot_directory=None,
        stderr=sys.stderr,  # if any, errors shall be printed to stderr
        working_directory=os.getcwd()
    ) as context:
        # start beacon_server as daemon
        main(context)
