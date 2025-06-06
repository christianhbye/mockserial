import threading
import time


class MockSerial:
    """
    A Serial-like object used for testing purposes. See pyserial's
    Serial class.
    """

    def __init__(self):
        self._read_buffer = bytearray()
        self._lock = threading.Lock()
        self.peer = None
        self.timeout = None

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
        self.peer = None
