import serial, time
import serial.tools.list_ports

BAUD = 115200

# Auto-detect Arduino port
ports = serial.tools.list_ports.comports()
PORT = None

for port in ports:
    if "USB" in port.description or "Arduino" in port.description:
        PORT = port.device
        break

if PORT is None:
    print("No Arduino found, available ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
    exit()

print(f"Connected to {PORT}...")
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(1.5)  

print("Reading data...")
try:
    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            print(line)
except KeyboardInterrupt:
    print("\nStopped reading")
    ser.close()
