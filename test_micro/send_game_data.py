import serial, time
import serial.tools.list_ports
import random

BAUD = 9600

# Mode configuration
MODES = {
    'male': {'min': 80, 'max': 200, 'name': 'Male Mode (Low Frequency)'},      
    'female': {'min': 250, 'max': 450, 'name': 'Female Mode (High Frequency)'} 
}

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.description or "Arduino" in port.description:
            return port.device, ports
    return None, ports

def send_set(ser,freq):
    ser.write(f"{freq}\n".encode())
    time.sleep(0.2)  # time for Arduino to read
    ser.close()

def select_mode():
    """Let user select male or female mode"""
    print("\n=== Select Mode ===")
    print("1. Male Mode (80-200 Hz)")
    print("2. Female Mode (250-450 Hz)")
    
    while True:
        choice = input("Choose mode (1/2): ").strip()
        if choice == '1':
            return 'male'
        elif choice == '2':
            return 'female'
        else:
            print("Invalid choice, please enter 1 or 2")

def main():

    PORT, PORTS = find_arduino_port()
    if not PORT:
        print("No Arduino found, available ports:")
        for port in PORTS:
            print(f"  {port.device}: {port.description}")
        raise SystemExit(1)

    # Select mode
    mode = select_mode()
    mode_config = MODES[mode]
    
    print(f"\nSelected: {mode_config['name']}")
    print(f"Frequency range: {mode_config['min']}-{mode_config['max']} Hz\n")  

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(1.5)

    # Generate target frequency based on mode
    target = random.randint(mode_config['min'], mode_config['max'])
    print(f"Target frequency: {target} Hz")
    send_set(ser,target)
    return target
