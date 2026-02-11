import serial, time
import serial.tools.list_ports
import random

BAUD = 9600

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.description or "Arduino" in port.description:
            return port.device, ports
    return None, ports

def send_set(ser,freq):
    ser.write(f"{freq}\n".encode())
    time.sleep(0.2)  # temps pour Arduino de lire
    ser.close()

def main():

    PORT, PORTS = find_arduino_port()
    if not PORT:
        print("No Arduino found, available ports:")
        for port in PORTS:
            print(f"  {port.device}: {port.description}")
        raise SystemExit(1)

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(1.5)
    target = random.randint(200,500)
    print(target)
    send_set(ser,target)
    return target
