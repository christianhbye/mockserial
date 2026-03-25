import threading
import time

try:
    from serial import (
        EIGHTBITS,
        PARITY_NONE,
        STOPBITS_ONE,
        SerialException,
        SerialTimeoutException,
    )
except ImportError:
    EIGHTBITS = 8
    PARITY_NONE = "N"
    STOPBITS_ONE = 1

    class SerialException(IOError):
        """Fallback when pyserial is not installed."""

        pass

    class SerialTimeoutException(SerialException):
        """Fallback when pyserial is not installed."""

        pass


class MockSerial:
    """
    A Serial-like object used for testing purposes. See pyserial's
    Serial class.
    """

    def __init__(
        self,
        port=None,
        baudrate=9600,
        bytesize=EIGHTBITS,
        parity=PARITY_NONE,
        stopbits=STOPBITS_ONE,
        timeout=None,
        xonxoff=False,
        rtscts=False,
        write_timeout=None,
        dsrdtr=False,
        inter_byte_timeout=None,
        exclusive=None,
        *,
        peer=None,
        simulate_timing=False,
    ):
        """
        Initialize the MockSerial instance.

        Accepts the same parameters as pySerial's ``Serial`` class.
        Hardware-level settings (baudrate, parity, etc.) are stored
        as attributes but do not affect mock behaviour.

        Parameters
        ----------
        port : str, optional
            Port name (stored but not used).
        baudrate : int
            Baud rate (stored, used by simulated timing).
        bytesize : int
            Number of data bits (stored).
        parity : str
            Parity setting (stored).
        stopbits : float
            Number of stop bits (stored).
        timeout : float, optional
            The timeout for read operations. If None, read
            operations will block indefinitely.
        xonxoff : bool
            Software flow control (stored).
        rtscts : bool
            Hardware (RTS/CTS) flow control (stored).
        write_timeout : float, optional
            Timeout for write operations (stored).
        dsrdtr : bool
            Hardware (DSR/DTR) flow control (stored).
        inter_byte_timeout : float, optional
            Inter-byte timeout (stored).
        exclusive : bool, optional
            Exclusive access mode (stored).
        peer : MockSerial, optional
            Keyword-only. The peer MockSerial instance to
            connect to.
        simulate_timing : bool
            Keyword-only. When True, ``flush()`` blocks
            proportionally to pending bytes at the configured
            baud rate, and ``write_timeout`` is enforced.
            Default False (instant writes, no-op flush).

        """
        self.port = port
        self.name = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.write_timeout = write_timeout
        self.dsrdtr = dsrdtr
        self.inter_byte_timeout = inter_byte_timeout
        self.exclusive = exclusive
        self.simulate_timing = simulate_timing
        self._read_buffer = bytearray()
        self._lock = threading.Lock()
        self._pending_bytes = 0
        if peer:
            self.add_peer(peer)
        else:
            self.peer = None

    def __eq__(self, other):
        """
        Check if two MockSerial instances are equal. They are considered
        equal if they are connected to the same peer.

        Parameters
        ----------
        other : MockSerial
            The other MockSerial instance to compare with.

        Returns
        -------
        bool
            True if both instances are connected to the same peer,
            False otherwise.

        """
        return isinstance(other, MockSerial) and self.peer is other.peer

    @property
    def is_open(self):
        """
        Check if the serial port is open. It is considered open if
        it has a peer connected.

        Returns
        -------
        bool
            True if the serial port is open, False otherwise.

        """
        try:
            return self.peer is not None
        except AttributeError:
            return False

    def add_peer(self, peer):
        """
        Add a peer MockSerial instance to this instance, and
        make this instance the peer of the given instance.

        Parameters
        ----------
        peer : MockSerial
            The peer MockSerial instance to connect to.

        Raises
        -------
        TypeError
            If the peer is not an instance of MockSerial.

        ValueError
            If the peer is already connected to another instance or
            this instance is already connected to a peer.

        """
        if self.is_open:
            if self.peer is peer:
                return
            raise ValueError("This instance is already connected to a peer")
        if not isinstance(peer, MockSerial):
            raise TypeError("Peer must be an instance of MockSerial")
        if peer.peer is not None:
            raise ValueError("Peer is already connected to another instance")
        self.peer = peer
        peer.peer = self

    @property
    def _bits_per_byte(self):
        """Total bits per byte including framing."""
        return (
            1  # start bit
            + self.bytesize
            + self.stopbits
            + (1 if self.parity != PARITY_NONE else 0)
        )

    def write(self, data):
        """
        Write data to serial port.

        When ``write_timeout`` is set, checks whether the
        accumulated pending bytes would exceed the timeout at the
        configured baud rate, and raises ``SerialTimeoutException``
        if so.

        Parameters
        ----------
        data : bytes
            The data to write.

        Returns
        -------
        int
            The number of bytes written.

        Raises
        -------
        SerialException
            If the serial port is not open.
        SerialTimeoutException
            If ``write_timeout`` is set and the simulated
            transmit time would exceed it.

        """
        peer = self.peer
        if peer is None:
            raise SerialException("Serial port is not open")
        with peer._lock:
            peer._read_buffer.extend(data)
        if self.simulate_timing:
            self._pending_bytes += len(data)
            if self.write_timeout is not None:
                delay = (
                    self._pending_bytes * self._bits_per_byte / self.baudrate
                )
                if delay > self.write_timeout:
                    raise SerialTimeoutException("Write timeout")
        return len(data)

    def read(self, size=1):
        """
        Read data from serial port. If a timeout is set, it may return
        less than the requested number of bytes.

        Parameters
        ----------
        size : int
            Maximum number of bytes to read.

        Returns
        -------
        bytes
            The data read from the serial port.

        """
        tstart = time.time()
        while True:
            with self._lock:
                if len(self._read_buffer) >= size:
                    data = self._read_buffer[:size]
                    self._read_buffer = self._read_buffer[size:]
                    return bytes(data)
                if self.timeout is not None:
                    if time.time() - tstart >= self.timeout:
                        data = self._read_buffer[:]
                        self._read_buffer.clear()
                        return bytes(data)
            time.sleep(0.01)

    def readline(self, size=None):
        """
        Read from the serial port until a newline character is found or
        until the specified size is reached. May return less than
        the requested size if a timeout is set.

        The timeout applies to the entire call, not per byte
        (matching pySerial behaviour).

        Parameters
        ----------
        size : int
            Maximum number of bytes to read.

        Returns
        -------
        bytes
            The line read from the serial port.

        """
        line = bytearray()
        tstart = time.time()
        while True:
            with self._lock:
                idx = self._read_buffer.find(b"\n")
                if idx >= 0:
                    end = idx + 1
                    if size is not None:
                        end = min(end, size - len(line))
                    line.extend(self._read_buffer[:end])
                    self._read_buffer = self._read_buffer[end:]
                    return bytes(line)
                if len(self._read_buffer) > 0:
                    take = len(self._read_buffer)
                    if size is not None:
                        take = min(take, size - len(line))
                    line.extend(self._read_buffer[:take])
                    self._read_buffer = self._read_buffer[take:]
                    if size is not None and len(line) >= size:
                        return bytes(line)
                if self.timeout is not None:
                    if time.time() - tstart >= self.timeout:
                        return bytes(line)
            time.sleep(0.01)

    @property
    def in_waiting(self):
        """
        Check how many bytes are waiting to be read.

        Returns
        -------
        int
            The number of bytes waiting to be read.

        """
        with self._lock:
            return len(self._read_buffer)

    def flush(self):
        """
        Flush the serial port.

        When ``simulate_timing`` is enabled, blocks for the time
        it would take to transmit all pending bytes at the
        configured baud rate. Otherwise this is a no-op.
        """
        if self.simulate_timing and self._pending_bytes > 0:
            delay = self._pending_bytes * self._bits_per_byte / self.baudrate
            time.sleep(delay)
            self._pending_bytes = 0

    def reset_input_buffer(self):
        """
        Clear the input buffer.
        """
        with self._lock:
            self._read_buffer.clear()

    def close(self):
        """
        Close the serial port.

        Thread-safe: acquires both peers' locks in a consistent
        order (by ``id``) to prevent deadlocks.
        """
        if not self.is_open:
            return
        peer = self.peer
        if peer is None:
            return
        first, second = sorted([self, peer], key=id)
        with first._lock:
            with second._lock:
                self.peer = None
                peer.peer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def create_serial_connection(timeout=None, **kwargs):
    """
    Create a mock serial connection between two MockSerial instances.

    Parameters
    ----------
    timeout : float
        The timeout for read operations. If specified, it will be set
        on both MockSerial instances.
    **kwargs
        Additional keyword arguments passed to ``MockSerial``.

    Returns
    -------
    MockSerial, MockSerial
        A pair of new instances of MockSerial, that can communicate
        with each other.

    """
    s1 = MockSerial(timeout=timeout, **kwargs)
    s2 = MockSerial(timeout=timeout, peer=s1, **kwargs)
    return s1, s2
