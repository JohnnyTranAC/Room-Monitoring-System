import RPi.GPIO as GPIO
import sys
import time
import datetime
import numpy as np
import Adafruit_DHT
import lcddriver
import speech_recognition as sr

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

### Set up LCD for status display
display = lcddriver.lcd()

### Set up DHT11 and array of last 3 temperatures
DHT_Sensor = Adafruit_DHT.DHT11
dht_pin = 21

temp_arr=[0] * 3
temp_cntr = 0

### Set up PIR Sensor for human detection
pir_pin = 11

GPIO.setup(pir_pin, GPIO.IN)

### Set up pushbuttons and LEDs
button1 = 22                 # Button 1 - Pin 22
button2 = 12                 # Button 2 - Pin 12
button3 = 13                 # Button 3 - Pin 13
button4 = 15                 # Button 4 - Pin 15
LED1 = 29                    # LED 1 - Pin 29
LED2 = 31                    # LED 2 - Pin 31
LED3 = 33                    # LED 3 - Pin 33

GPIO.setup(button1,GPIO.IN,pull_up_down=GPIO.PUD_UP) # Set buttons as input
GPIO.setup(button2,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(button3,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(button4,GPIO.IN,pull_up_down=GPIO.PUD_UP)

GPIO.setup(LED1,GPIO.OUT) # Set LEDs as output
GPIO.setup(LED2,GPIO.OUT)
GPIO.setup(LED3,GPIO.OUT)

occupied = False
doorOpen = False

temperature1=True
ignore_temp1=False

### Initialize system status
doorStatus = "SAFE"

try:
    while(1):
        # First temperature is not displayed until an average temperature can be calculated for accuracy
        if ignore_temp1==False:
            display.lcd_clear()
            display.lcd_display_string("Current Time:", 1)
            display.lcd_display_string(str(datetime.datetime.now().time()), 2)
        
        humidity, temperature = Adafruit_DHT.read_retry(DHT_Sensor, dht_pin)
        print("Temp: {0:0.1f}C\tHumidity: {1:1.0f}%\n".format((9/5)*int(temperature)+32, humidity))
        
        # Flag for 10 second pause when PIR sensor detects, continue if no further motion
        if GPIO.input(pir_pin) and occupied == False:
            print("Person detected, turning on room light")
            occupied = True
            GPIO.output(LED3,True)
        elif GPIO.input(pir_pin) == 0 and occupied == True:
            time.sleep(10)
            occupied = False
            GPIO.output(LED3,False)
        
        # Get temperature for user to adjust
        # Using average humidity for Irvine of 75 for weather index
        if ignore_temp1==True:
            if temperature1==True:
                user_temperature = round((9/5)*int(temperature)+32 + 0.05*75)
                temperature1=False
                print(user_temperature)
        
            if GPIO.input(button1)==0:                  # Button 1: Reduce user-desired temperature; 65 lowest
                if user_temperature >= 65:
                    user_temperature -= 1
                    print("Decreasing temperature")
                else:
                    print("Cannot be lower temperature")
            if GPIO.input(button2)==0:                  # Button 2: Increase user-desired temperature; 85 highest
                if user_temperature <= 85:
                    user_temperature += 1
                    print("Increasing temperature")
                else:
                    print("Cannot be higher temperature")
            if GPIO.input(button3)==0:                   # Button 3: Open/closes door&window then pause system for 3 seconds
                if doorOpen==False:
                    display.lcd_clear()
                    display.lcd_display_string("DOOR/WINDOW OPEN", 1)
                    display.lcd_display_string("  HVAC HALTED", 2)
                    doorStatus = "OPEN"
                    doorOpen=True
                    time.sleep(3)
                else:
                    display.lcd_clear()
                    display.lcd_display_string("DOOR/WINDW CLOSE", 1)
                    display.lcd_display_string(" HVAC CONTINUE", 2)
                    doorStatus = "SAFE"
                    doorOpen=False
                    time.sleep(3)
                    if acStatus == "ON ":                 # Temporarily turn off any HVAS that are on for 3 seconds
                        acStatus = "OFF"
                        GPIO.output(LED1, False)
                        time.sleep(3)
                        acStatus = "ON "
                        GPIO.output(LED1, True)
                    elif heaterStatus == "ON ":
                        heaterStatus = "OFF"
                        GPIO.output(LED2, False)
                        time.sleep(3)
                        heaterStatus = "ON "
                        GPIO.output(LED2, True)
                    elif acStatus == "ON " and heaterStatus == "ON ":
                        acStatus = "OFF"
                        heatStatus = "OFF"
                        GPIO.output(LED1, False)
                        GPIO.output(LED2, False)
                        time.sleep(3)
                        acStatus = "ON "
                        heaterStatus = "ON "
                        GPIO.output(LED1, True)
                        GPIO.output(LED2, True)
            if GPIO.input(button4)==0:                   # Button 4: System enters voice recognition
                r = sr.Recognizer()
                m = sr.Microphone()
                
                print("Say something!")
                with m as source: audio = r.listen(source)
                print("Got it! Now to recognize it...")
                
                try:
                    # Recognize speech using Google Speech Recognition
                    transcribe = r.recognize_google(audio)
                    
                    if transcribe.find('ac')!=-1:
                        if transcribe.find('on')!=-1:
                            acStatus = "ON "
                            GPIO.output(LED1, True)
                        elif transcribe.find('off')!=-1:
                            acStatus = "OFF"
                            GPIO.output(LED1, False)
                    if transcribe.find('heater')!=-1:
                        if transcribe.find('on')!=-1:
                            heaterStatus = "ON "
                            GPIO.output(LED2, True)
                        elif transcribe.find('off')!=-1:
                            heaterStatus = "OFF"
                            GPIO.output(LED2, False)
                    if transcribe.find('door')!=-1:
                        if transcribe.find('open')!=-1:
                            display.lcd_clear()
                            display.lcd_display_string("DOOR/WINDOW OPEN", 1)
                            display.lcd_display_string("  HVAC HALTED", 2)
                            doorStatus = "OPEN"
                            doorOpen=True
                            time.sleep(3)
                        elif transcribe.find('close')!=-1:
                            display.lcd_clear()
                            display.lcd_display_string("DOOR/WINDW CLOSE", 1)
                            display.lcd_display_string(" HVAC CONTINUE", 2)
                            doorStatus = "SAFE"
                            doorOpen=False
                            time.sleep(3)
                    
                    if transcribe.find('goodbye')!=-1:    # Close program
                        print("Goodbye")
                        break
                except sr.UnknownValueError:
                    print("Oops! Didn't catch that")
                except sr.RequestError as e:
                    print("Uh oh! Couldn't request results from Google Speech Recognition service; {0}".format(e))
            
            # Turn on ac/heater is user wants temp 3 degrees below/above average
            # Using average humidity for Ivine of 75 for weather index
            if user_temperature <= round((9/5)*int(temperature)+32 + 0.05*75) - 3:
                acStatus = "ON "
                GPIO.output(LED1, True)
            else:
                acStatus = "ON "
                GPIO.output(LED1, True)
            if user_temperature >= round((9/5)*int(temperature)+32 + 0.05*75) + 3:
                heatStatus = "ON "
                GPIO.output(LED2, True)
            else:
                heatStatus = "OFF"
                GPIO.output(LED2, False)
            
            # Calculate temperature to average of last 3 non-zero values
            temp_arr[temp_cntr] = (9/5)*int(temperature)+32 + 0.05*75
            a = np.array(temp_arr)
            average_temp = round(a[np.nonzero(a)].mean(), 0)
            temp_cntr += 1
            if temp_cntr > 2:
                temp_cntr = 0
            
            # Display default summary status on LCD by temperature, door status, and HVAS statuses
            status1_top = str(average_temp) + "/" + str(user_temperature) + "   D:" + doorStatus
            status1_btm = "H:" + heatStatus + "      L:" + acStatus
            display.lcd_display_string(status1_top, 1)
            display.lcd_display_string(status1_btm, 2)
        
        # First temperature recorded may not be accurate
        # so set flag to record second temperature onwards
        if ignore_temp1==False:
            ignore_temp1=True
            
# If there is a KeyboardInterrupt (when you press ctrl+c), exit the program and cleanup
except KeyboardInterrupt:
    print("Cleaning up!")
    GPIO.output(LED1,False)
    GPIO.output(LED2,False)
    GPIO.output(LED3,False)
    display.lcd_clear()
    display.lcd_display_string("Powering down",1)
    display.lcd_display_string(str(datetime.datetime.now().time()), 2)  # Display time when system shuts off
    time.sleep(2)
    display.lcd_clear()
