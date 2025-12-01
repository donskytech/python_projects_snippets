import serial
import time

# Create a Serial Object to communicate with our USB to GSM 800C
ser = serial.Serial(
    port='COM9',        
    baudrate=9600,     
    timeout=2,         
    xonxoff=False,     
    rtscts=False,     
    dsrdtr=False      
)

def send_at_command(command, delay=2):
    ser.write((command + '\r\n').encode()) 
    print("Waiting for AT Response")
    time.sleep(delay)                       
    response = ser.read_all().decode('utf-8')
    return response

try:
    print("Testing SIM800C Module...")

    # Check AT Command Response
    response = send_at_command("AT")
    print("Response to AT: ", response)

    # Check SIM card status
    response = send_at_command("AT+CPIN?")
    print("SIM Card Status: ", response)

    # Check Network Registration
    response = send_at_command("AT+CREG?")
    print("Network Registration: ", response)

    # Check Signal Strength
    response = send_at_command("AT+CSQ")
    print("Signal Strength: ", response)

    # Check Operator Name
    response = send_at_command("AT+COPS?")
    print("Operator Name: ", response)

    # Test SMS Sending (Optional)
    response = send_at_command('AT+CMGF=1')
    print("SMS Mode Set: ", response)

    # Replace with your phone number
    phone_number = "+639082233631"
    message = "Testing from DonskyTech from SIM800C USB to GSM Module"
    send_at_command(f'AT+CMGS="{phone_number}"')
    time.sleep(1)
    ser.write((message + '\x1A').encode())
    print("Message Sent!")

except Exception as e:
    print("Error: ", e)

finally:
    ser.close()
