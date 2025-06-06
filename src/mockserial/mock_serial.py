import threading
import time


class MockSerial:
    """
    A Serial-like object used for testing purposes. See pyserial's
    Serial class.
    """

    def __init__(self, peer=None, timeout=None):
        """
        Initialize the MockSerial instance.

        Parameters
        ----------
        peer : MockSerial
            The peer MockSerial instance to which this instance will
            be connected. If None, this instance will not be connected
            to any other instance.
        timeout : float, optional
            The timeout for read operations. If None, read operations
            will block indefinitely.

        """
        self._read_buffer = bytearray()
        self._lock = threading.Lock()
        self.timeout = timeout
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

    def write(self, data):
        """
        Write data to serial port.

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
        RuntimeError
            If the serial port is not open.

        """
        if not self.peer:
            raise RuntimeError("Serial port is not open")
        with self.peer._lock:
            self.peer._read_buffer.extend(data)
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
                elapsed = time.time() - tstart
                if elapsed >= self.timeout:
                    data = self._read_buffer[:]  # less than requested
                    self._read_buffer.clear()
                    return bytes(data)
            time.sleep(0.01)

    def readline(self, size=None):
        """
        Read from the serial port until a newline character is found or
        until the specified size is reached. May return less than
        the requested size if a timeout is set.

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
        while True:
            char = self.read(1)
            if not char:
                break
            line.extend(char)
            if char == b"\n":
                break
            if size is not None and len(line) >= size:
                break
        return bytes(line)

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
        No-op for flushing the serial port.
        """
        pass

    def reset_input_buffer(self):
        """
        Clear the input buffer.
        """
        with self._lock:
            self._read_buffer.clear()

    def close(self):
        """
        Close the serial port.
        """
        if self.is_open:
            self.peer.peer = None
            self.peer = None


def create_serial_connection(timeout=None):
    """
    Create a mock serial connection between two MockSerial instances.

    Parameters
    ----------
    timeout : float
        The timeout for read operations. If specified, it will be set
        on both MockSerial instances.

    Returns
    -------
    MockSerial, MockSerial
        A pair of new instances of MockSerial, that can communicate
        with each other.

    """
    s1 = MockSerial(timeout=timeout)
    s2 = MockSerial(peer=s1, timeout=timeout)
    return s1, s2
