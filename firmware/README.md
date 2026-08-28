# Pico-DAQ-Firmware

`main.py` ist die MicroPython-Anwendung für den Raspberry Pi Pico. Sie wartet
über USB-CDC auf `START\n` und `STOP\n`. Während einer laufenden Messung erzeugt
der Hardware-Timer alle 10 ms einen Messwert und sendet CSV-Zeilen im Format:

```text
<timestamp_ms>,<value>
```

Bei jedem `START` werden Zeitstempel und Messwert auf null zurückgesetzt. Die
ersten Datensätze einer Messung lauten damit:

```text
0,0
10,1
20,2
```

Nach der einmaligen Installation der zum Board passenden MicroPython-UF2 wird
die Anwendung aus dem Projektverzeichnis übertragen:

```bash
uvx mpremote connect auto fs cp firmware/main.py :main.py
```

Anschließend den Pico neu starten. MicroPython führt `main.py` beim Start
automatisch aus.
