"""MicroPython application for the Raspberry Pi Pico DAQ demonstrator.

Install the matching MicroPython UF2 first, then copy this file to the Pico as
``main.py``. Protocol on USB CDC:

    PC -> Pico: START\n / STOP\n
    Pico -> PC: <timestamp_ms>,<value>\n
"""

import micropython
import select
import sys
import time
from machine import Timer

SAMPLE_PERIOD_MS = 10  # 100 Hz

_timer = Timer()
_running = False
_next_value = 0
_generation = 0

def _emit_sample(generation):
    """Run outside the timer IRQ and emit one complete CSV record."""
    global _next_value

    if not _running or generation != _generation:
        return

    # Use a measurement-relative timestamp. Every START resets _next_value,
    # therefore the first record is 0,0 and subsequent records advance by
    # exactly the configured timer period (10,1; 20,2; ...).
    timestamp_ms = _next_value * SAMPLE_PERIOD_MS
    sys.stdout.write("{},{}\n".format(timestamp_ms, _next_value))
    _next_value += 1


def _timer_tick(_):
    """Keep USB output and string allocation outside the hardware-timer IRQ."""
    try:
        micropython.schedule(_emit_sample, _generation)
    except RuntimeError:
        # If the host stalls and the scheduler queue fills, drop this sample.
        pass


def start_acquisition():
    global _generation, _running, _next_value

    _timer.deinit()
    _generation = (_generation + 1) & 0x3FFFFFFF
    _next_value = 0
    _running = True
    _timer.init(
        mode=Timer.PERIODIC,
        period=SAMPLE_PERIOD_MS,
        callback=_timer_tick,
    )


def stop_acquisition():
    global _running

    _running = False
    _timer.deinit()


def handle_command(command):
    command = command.strip().upper()
    if command == "START":
        start_acquisition()
    elif command == "STOP":
        stop_acquisition()


def main():
    """Poll USB CDC without blocking scheduled sample transmission."""
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    command_buffer = ""

    while True:
        if poller.poll(0):
            character = sys.stdin.read(1)
            if character in ("\n", "\r"):
                if command_buffer:
                    handle_command(command_buffer)
                    command_buffer = ""
            elif character:
                command_buffer += character

        time.sleep_ms(1)


micropython.alloc_emergency_exception_buf(100)

try:
    main()
finally:
    stop_acquisition()
