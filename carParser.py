import threading
import time

import serial

__all__ = [
    "init",
    "stop",
    "getIMU",
    "getDIST",
    "getADC",
    "getButton",
    "getColor",
    "getObstacle",
    "move",
    "beep",
    "servo",
    "led",
]

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_ser = None
_read_thread = None
_running = False

_lock = threading.Lock()

_latest = {
    "IMU": [0.0] * 9,
    "DIST": [0.0] * 4,
    "ADC": [0.0] * 4,
    "BUTTON": [0.0] * 2,
    "COLOR": [0.0] * 4,
    "OBSTACLE": [0.0, 0.0],  # [val, timestamp]
}

_EXPECTED_FIELDS = {
    "IMU": 9,
    "DIST": 4,
    "ADC": 4,
    "BUTTON": 2,
    "COLOR": 4,
    "OBSTACLE": 1,
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _to_number(s):
    """Convert a field to int if possible, else float. Raises ValueError
    on failure (caller should catch and drop the line)."""
    try:
        return int(s)
    except ValueError:
        return float(s)


def _parse_line(line):
    line = line.strip()
    if not line or not line.startswith("$"):
        return

    parts = line[1:].split(",")
    if not parts:
        return

    tag = parts[0]
    fields = parts[1:]

    expected = _EXPECTED_FIELDS.get(tag)
    if expected is None:
        return  # unknown tag, ignore
    if len(fields) != expected:
        return  # malformed, ignore

    try:
        values = [_to_number(f) for f in fields]
    except ValueError:
        return  # non-numeric field, ignore

    with _lock:
        if tag == "OBSTACLE":
            _latest["OBSTACLE"] = [values[0], time.time()]
        else:
            _latest[tag] = values


def _read_loop():
    global _running
    buf = b""
    while _running:
        try:
            chunk = _ser.read(_ser.in_waiting or 1)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw_line, buf = buf.split(b"\n", 1)
                try:
                    line = raw_line.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                _parse_line(line)
        except serial.SerialException:
            break
        except Exception:
            # Never let the reader thread die on a transient error
            continue


# ---------------------------------------------------------------------------
# Public: init / stop
# ---------------------------------------------------------------------------

def init(com, baud, timeout=0):
    """Open the serial port and start the background parser thread.

    com: string, e.g. "/dev/AMA0"
    baud: int, e.g. 921600

    Returns True on success, False on failure (port could not be opened,
    thread could not be started, etc). Does not raise.
    """
    global _ser, _read_thread, _running

    try:
        if _running:
            stop()

        _ser = serial.Serial(com, baud, timeout=timeout)
        _running = True
        _read_thread = threading.Thread(target=_read_loop, daemon=True)
        _read_thread.start()
        return True
    except Exception:
        _running = False
        _ser = None
        _read_thread = None
        return False


def stop():
    """Stop the background thread and close the serial port."""
    global _running, _ser, _read_thread

    _running = False
    if _read_thread is not None:
        _read_thread.join(timeout=1)
        _read_thread = None
    if _ser is not None:
        try:
            _ser.close()
        except Exception:
            pass
        _ser = None


# ---------------------------------------------------------------------------
# Public: getters
# ---------------------------------------------------------------------------

def getIMU():
    with _lock:
        return list(_latest["IMU"])


def getDIST():
    with _lock:
        return list(_latest["DIST"])


def getADC():
    with _lock:
        return list(_latest["ADC"])


def getButton():
    with _lock:
        return list(_latest["BUTTON"])


def getColor():
    with _lock:
        return list(_latest["COLOR"])


def getObstacle():
    with _lock:
        return list(_latest["OBSTACLE"])


# ---------------------------------------------------------------------------
# Public: writers
# ---------------------------------------------------------------------------

def _write(msg):
    """Write a command line to the serial port.

    Returns True on success, False on failure (port not initialized,
    port closed, write error, etc). Does not raise.
    """
    if _ser is None:
        return False
    try:
        _ser.write((msg + "\n").encode("utf-8"))
        return True
    except Exception:
        return False


def move(a, b, c):
    return _write(f"$MOVE,{a},{b},{c}")


def beep(a, b):
    return _write(f"$BEEP,{a},{b}")


def servo(a, b, c, d):
    return _write(f"$SERVO,{a},{b},{c},{d}")


def led(a, b):
    return _write(f"$LED,{a},{b}")
