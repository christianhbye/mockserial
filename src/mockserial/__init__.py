from importlib.metadata import version

from .mock_serial import MockSerial, create_serial_connection

__version__ = version("pyserial-mock")
