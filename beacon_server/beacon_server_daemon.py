#
# THU - Team Oriented Project - WS20/21
#
"""
The server component of the beacon monitoring system
"""
from typing import Tuple, Dict
import socket
import json
import sys
import os

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

    def __init__(self, ip_port: Tuple[str, int], queue_id: str):
        self.ip_port = ip_port
        self.queue_id = queue_id

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
            msg_and_node = self.sock.recvfrom(self.DEFAULT_BUFFER_SIZE)
            try:
                self.ipc_queue.put_nowait(msg_and_node)
            except posixmq.queue.Full:
                # queue is full -> nobody's listening on the other side. nothing to do.
                pass


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

            return BeaconServer(ip_port=(ip, port), queue_id=queue_id)

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


def main():
    factory = ServerFactory()
    server = factory.from_config_file("config.json")
    server.start()


if __name__ == '__main__':
    # start beacon as daemon
    # TODO: optionally get config file path from stdin
    config_file = open("config.json", 'r')
    with daemon.DaemonContext(
            files_preserve=[config_file],
            chroot_directory=None,
            stderr=sys.stderr,  # if any, errors shall be printed to stderr
            working_directory=os.getcwd()
    ):
        main()

# msg, node = (
#     b'\x80\x04\x95\x89\x00\x00\x00\x00\x00\x00\x00}\x94(\x8c\x08platform\x94\x8c,'
#     b'Linux-5.4.0-48-generic-x86_64-with-glibc2.29\x94\x8c\x06system\x94\x8c\x05Linux'
#     b'\x94\x8c\x03cpu\x94\x8c\x06x86_64\x94\x8c\tcpu_usage\x94G@\x04\x00\x00\x00\x00\x00'
#     b'\x00\x8c\tmem_usage\x94G@I\x10pP\x83\xc4\x8au.',
#     ('127.0.0.1', 59338)
# )
