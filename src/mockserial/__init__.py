from importlib.metadata import version

from .mock_serial import (  # noqa: F401
    EIGHTBITS,
    PARITY_NONE,
    STOPBITS_ONE,
    MockSerial,
    SerialException,
    SerialTimeoutException,
    create_serial_connection,
)

__version__ = version("pyserial-mock")
