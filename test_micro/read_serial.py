import serial, time

PORT = "COM5"      
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(1.5)  

print("Reading...")
while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if line:
        print(line)
