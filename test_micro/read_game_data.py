import serial, time
import serial.tools.list_ports

BAUD = 9600

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.description or "Arduino" in port.description:
            return port.device, ports
    return None, ports

def send_set(ser, freq):
    ser.write(f"SET {freq}\n".encode("utf-8"))

def parse_frequency(line: str):
    text = line.strip()
    if not text:
        return None
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    if text.lower().endswith("hz"):
        text = text[:-2].strip()
    try:
        return float(text)
    except ValueError:
        return None

PORT, PORTS = find_arduino_port()
if not PORT:
    print("No Arduino found, available ports:")
    for port in PORTS:
        print(f"  {port.device}: {port.description}")
    raise SystemExit(1)

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(1.5)

while True:
    line = ser.readline().decode("utf-8", errors="ignore")
    if not line:
        continue
    # Print all incoming data for debugging
    print(f"[raw] {line.strip()}")
    freq = parse_frequency(line)
    if freq is not None:
        print(f"[freq] {freq}")
