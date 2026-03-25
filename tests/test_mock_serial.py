import pytest
import threading
import time

from mockserial import MockSerial, create_serial_connection


def test_add_peer():
    serial = MockSerial()
    peer = MockSerial()
    assert not serial.is_open
    assert not peer.is_open
    serial.add_peer(peer)
    assert peer == serial.peer
    assert serial == peer.peer
    assert serial.is_open
    assert peer.is_open

    # connect serial and peer, add second peer fails
    serial = MockSerial()
    peer = MockSerial(peer=serial)
    assert peer.peer == serial
    assert serial.peer == peer
    peer2 = MockSerial()
    with pytest.raises(ValueError):
        serial.add_peer(peer2)
    # or fails if add a peer that is already connected
    serial = MockSerial()
    peer = MockSerial(peer=serial)
    serial2 = MockSerial()
    with pytest.raises(ValueError):
        serial2.add_peer(peer)  # peer already connected to serial
    # works if connecting same peer again
    serial = MockSerial()
    peer = MockSerial(peer=serial)
    assert serial.peer == peer
    serial.add_peer(peer)  # no error
    assert serial.peer == peer  # still the same peer
    # invalid peer type
    serial = MockSerial()
    with pytest.raises(TypeError):
        serial.add_peer("not a peer")


def test_write_no_peer():
    serial = MockSerial()
    with pytest.raises(RuntimeError):
        serial.write(b"Hello")


@pytest.mark.parametrize(
    "timeout, data, expected",
    [(None, b"Hello", b"Hello"), [0.1, b"Hello", b"Hello"], [0.1, b"", b""]],
)
def test_read_write(timeout, data, expected):
    sa, sb = create_serial_connection(timeout=timeout)
    written = sa.write(data)
    assert written == len(data)
    tstart = time.time()
    if data:
        size = len(data)
    else:
        size = 1
    read = sb.read(size=size)
    elapsed = time.time() - tstart
    assert read == expected
    if data:
        assert elapsed < 0.1
    else:
        assert elapsed >= timeout


def test_read_chunked():
    sa, sb = create_serial_connection()
    n = sa.write(b"Hello")
    assert n == 5
    assert sb.in_waiting == 5
    sb.write(b"World")
    assert sa.in_waiting == 5
    read = sa.read(size=3)
    assert read == b"Wor"
    assert sa.in_waiting == 2
    read = sa.read(size=2)
    assert read == b"ld"


def test_readline():
    sa, sb = create_serial_connection(timeout=0.2)
    sa.write(b"Hello\nWorld\n")
    assert sb.readline() == b"Hello\n"
    assert sb.in_waiting == 6
    assert sb.readline() == b"World\n"
    assert sb.readline() == b""

    # read line but size < len(line)
    sb.reset_input_buffer()
    sa.write(b"123456\n789")
    read = sb.readline(size=3)
    assert read == b"123"
    assert sb.in_waiting == 7
    read = sb.readline()
    assert read == b"456\n"
    assert sb.in_waiting == 3
    # no more newline, should read until timeout
    tstart = time.time()
    read = sb.readline()
    elapsed = time.time() - tstart
    assert read == b"789"
    assert sb.in_waiting == 0
    assert elapsed >= 0.2

    # read nothing
    sb.reset_input_buffer()
    tstart = time.time()
    read = sb.readline()
    elapsed = time.time() - tstart
    assert read == b""
    assert sb.in_waiting == 0
    assert elapsed >= 0.2


def test_reset_input_buffer():
    sa, sb = create_serial_connection()
    sa.write(b"Hello")
    assert sb.in_waiting == 5
    sb.reset_input_buffer()
    assert sb.in_waiting == 0

    # flush input buffer (no-op)
    sb.flush()
    assert sb.in_waiting == 0


def test_close():
    serial, peer = create_serial_connection()
    assert serial.is_open
    assert peer.is_open
    assert serial.peer == peer
    assert peer.peer == serial
    serial.close()
    assert not serial.is_open
    assert not peer.is_open


def test_in_waiting_is_property():
    """in_waiting must be a property (not a method) to match pySerial."""
    sa, sb = create_serial_connection()
    # Without data, in_waiting should be falsy (0)
    assert not sb.in_waiting
    assert sb.in_waiting == 0
    sa.write(b"X")
    # With data, in_waiting should be truthy (nonzero int)
    assert sb.in_waiting
    assert sb.in_waiting == 1


def test_read_timeout_thread_safety():
    """read() timeout path must hold the lock."""
    sa, sb = create_serial_connection(timeout=0.05)

    def writer():
        for _ in range(100):
            try:
                sa.write(b"X")
            except Exception:
                pass
            time.sleep(0.001)

    t = threading.Thread(target=writer)
    t.start()
    # Repeatedly timeout-read to exercise the timeout path
    for _ in range(50):
        sb.read(10)
    t.join()
    # If there was a race, we'd see exceptions or corruption


def test_readline_cumulative_timeout():
    """readline() timeout applies to the entire call, not per byte."""
    sa, sb = create_serial_connection(timeout=0.2)
    sa.write(b"no newline here")
    tstart = time.time()
    result = sb.readline()
    elapsed = time.time() - tstart
    assert result == b"no newline here"
    assert elapsed >= 0.2
    assert elapsed < 0.5  # must NOT be 0.2 * 15 = 3.0
