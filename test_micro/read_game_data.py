import serial, time
import serial.tools.list_ports

BAUD = 9600

def find_arduino_port(): # on cherche le port arduino
    ports = serial.tools.list_ports.comports() 
    for port in ports:
        if "USB" in port.description or "Arduino" in port.description:
            return port.device, ports
    return None, ports

def parse_frequency(line: str): # retourne la fréquence seule
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

def main_r(): 
    PORT, PORTS = find_arduino_port() # on trouve le port arduino
    if not PORT:
        print("No Arduino found, available ports:")
        for port in PORTS:
            print(f"  {port.device}: {port.description}")
        raise SystemExit(1)

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(1.5)

    while True:
        line = ser.readline().decode("utf-8", errors="ignore") # on lit ce qu'il nous envoie
        if not line:
            continue
        freq = parse_frequency(line) # si elle existe, on extrait la fréquence du message
        if freq is not None:
            return freq 
