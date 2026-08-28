import time
import unittest
from collections import deque
from unittest.mock import patch

import serial

from daq import (
    DAQController,
    DAQSource,
    PicoDAQReader,
    SimulatorDAQReader,
    SourceKind,
)


class FakeSerial:
    instances = []

    def __init__(self, **_kwargs):
        self.is_open = True
        self.writes = []
        self.lines = deque([b"1000,0\n", b"1010,1\n", b"1020,2\n"])
        self.__class__.instances.append(self)

    def reset_input_buffer(self):
        pass

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        pass

    def readline(self):
        if self.lines:
            return self.lines.popleft()
        time.sleep(0.005)
        return b""

    def close(self):
        self.is_open = False


class DAQBackendTests(unittest.TestCase):
    def test_simulator_generates_100_hz_sequence(self):
        reader = SimulatorDAQReader()
        reader.start()
        time.sleep(0.125)
        reader.stop()

        rows = reader.snapshot()
        self.assertGreaterEqual(len(rows), 10)
        self.assertLessEqual(len(rows), 16)
        self.assertEqual([value for _, value in rows], list(range(len(rows))))
        reader.close()

    def test_pico_reader_uses_serial_protocol_only(self):
        FakeSerial.instances.clear()
        with patch("daq.pico.serial.Serial", FakeSerial):
            reader = PicoDAQReader("COM_TEST")
            reader.start()
            time.sleep(0.025)
            reader.stop()

        self.assertEqual(reader.snapshot(), [(1000, 0), (1010, 1), (1020, 2)])
        self.assertEqual(FakeSerial.instances[0].writes, [b"START\n", b"STOP\n"])
        reader.close()

    def test_pico_failure_does_not_start_simulator(self):
        source = DAQSource(
            kind=SourceKind.PICO,
            label="Pico test",
            port="INVALID_PORT",
        )
        controller = DAQController()
        controller.select_source(source)

        with patch(
            "daq.pico.serial.Serial",
            side_effect=serial.SerialException("nicht erreichbar"),
        ):
            with self.assertRaises(ConnectionError):
                controller.start()

        time.sleep(0.03)
        state = controller.status_snapshot()
        self.assertEqual(state["mode"], "error")
        self.assertFalse(state["running"])
        self.assertEqual(controller.snapshot(), [])
        controller.close()


if __name__ == "__main__":
    unittest.main()
