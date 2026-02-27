import serial, time
import serial.tools.list_ports
import random

BAUD = 9600

# Définitions des modes de configuration
MODES = {
    'male': {'min': 80, 'max': 200, 'name': 'Male Mode (Low Frequency)'},      
    'female': {'min': 250, 'max': 450, 'name': 'Female Mode (High Frequency)'} 
}

def find_arduino_port(): # on trouve le port arduino
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.description or "Arduino" in port.description:
            return port.device, ports
    return None, ports

def send_set(ser,freq): # on envoie la fréquence vers l'arduino
    ser.write(f"{freq}\n".encode())
    time.sleep(0.2)  # délai pour que l'Arduino ait le temps de lire
    ser.close()

def select_mode(): # sélection du mode
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

    PORT, PORTS = find_arduino_port() # on trouve le port arduino
    if not PORT:
        print("No Arduino found, available ports:")
        for port in PORTS:
            print(f"  {port.device}: {port.description}")
        raise SystemExit(1)

    # Selection du mode
    mode = select_mode()
    mode_config = MODES[mode]
    
    print(f"\nSelected: {mode_config['name']}")
    print(f"Frequency range: {mode_config['min']}-{mode_config['max']} Hz\n")  

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(1.5)

    # On génère une fréquence cible aléatoire selon le mode
    target = random.randint(mode_config['min'], mode_config['max'])
    print(f"Target frequency: {target} Hz")
    send_set(ser,target) # on envoie cette fréquence vers arduino
    return target
