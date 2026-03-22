#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_NeoPixel.h>


#define LED_STRING_LENGTH 47
#define LED_pin 18

// NeoPixel Configuration
Adafruit_NeoPixel pixels(LED_STRING_LENGTH, LED_pin, NEO_GRB + NEO_KHZ800);

// WiFi credentials
const char* ssid = "OCEANWALK2";
const char* password = "ilovetom";  // Replace with your actual password

// UDP Configuration
const char* udpAddress = "192.168.0.173";  // IP address of computer running udp_controller.py
const int udpPortTX = 5007;  // Port where udp_controller.py is listening
const int udpPortRX = 5008;  // Port to receive color commands from grid app

WiFiUDP udp;
const int input_pin_A = 23;
const int input_pin_B = 21;
const int pwm_pin = 22;
const int LEDC_CHANNEL = 0;
const int LEDC_FREQ = 38000;  // 38 kHz for IR control
const int LEDC_RESOLUTION = 10;  // 10-bit resolution (0-1023)


// Message variable
String message = "";

// RGB Color structure
struct RGBColor {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
};

// Color enum
enum Color {
  BLUE = 0,
  GREEN = 1,
  RED = 2
};

// Color map - maps enum values to RGB colors
RGBColor colorMap[] = {
  {0, 0, 255},      // BLUE = 0
  {0, 255, 0},      // GREEN = 1
  {255, 0, 0}       // RED = 2
};

// Interrupt variables
volatile bool pinStateChanged22 = false;
volatile bool pinStateChanged23 = false;
volatile unsigned long lastInterruptTime = 0;


// Timer interrupt variables
hw_timer_t *timer = NULL;
volatile bool timerFlag = false;

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 1000;  // Send every 1 second (1000 ms)

// Interrupt Service Routine for pin 23
void IRAM_ATTR pin23ISR() 
{
    pinStateChanged23 = true;
}

// Interrupt Service Routine for pin 21
void IRAM_ATTR pin21ISR() 
{
    pinStateChanged22 = true;
}

// Timer interrupt service routine - fires every 10ms
void IRAM_ATTR onTimer() 
{
    timerFlag = true;
}

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\nESP32 Base Code - UDP Click Sender");
  Serial.println("===================================");
  
  // Disconnect from any previous connection
  WiFi.disconnect(true);
  delay(1000);
  
  // Set WiFi to station mode
  WiFi.mode(WIFI_STA);
  
  // Print MAC address
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
  
  // Connect to WiFi
  Serial.print("Connecting to SSID: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  // Wait for connection with timeout
  int attempts = 0;
  int maxAttempts = 40; // 20 seconds timeout
  
  while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts) 
  {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.println();
  
  // Check if connected
  if (WiFi.status() == WL_CONNECTED) 
  {
    Serial.println("\n*** WiFi Connected Successfully! ***");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("MAC Address: ");
    Serial.println(WiFi.macAddress());
    Serial.print("Signal Strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.println();
    Serial.print("Sending UDP packets to: ");
    Serial.print(udpAddress);
    Serial.print(":");
    Serial.println(udpPortTX);
    Serial.println("===================================\n");
    
    // Initialize UDP
    udp.begin(udpPortRX);

    pinMode(input_pin_A, INPUT_PULLUP);
    pinMode(input_pin_B, INPUT_PULLUP);
    
    // Attach interrupt to pin 23 (triggers on CHANGE - both rising and falling edges)
    attachInterrupt(digitalPinToInterrupt(input_pin_A), pin23ISR, RISING);
    attachInterrupt(digitalPinToInterrupt(input_pin_B), pin21ISR, RISING);

    Serial.println("Interrupt attached to pin 23");

    // Configure pin 22 for 38 kHz PWM output
    ledcAttach(pwm_pin, LEDC_FREQ, LEDC_RESOLUTION);
    ledcWrite(pwm_pin, 512);  // Set 50% duty cycle (512 out of 1023 for 10-bit)
    
    Serial.println("Pin 22 configured for 38 kHz PWM output");
    
    // Initialize NeoPixels on pin 18
    pixels.begin();

    // Set all pixels to white
    for (int i = 0; i < LED_STRING_LENGTH; i++) 
    {
      pixels.setPixelColor(i, pixels.Color(40, 40, 40));  // Start with dim white
    }
    pixels.show();
    
    Serial.println("Pin 18 configured for NeoPixels (" + String(LED_STRING_LENGTH) + " pixels)");
    
    // Configure hardware timer for 10ms interrupt
    // Timer 0, prescaler 80 (80MHz/80 = 1MHz = 1us per tick)
    timer = timerBegin(1000000);  // 1 MHz (1 microsecond resolution)
    
    // Attach the interrupt function
    timerAttachInterrupt(timer, &onTimer);
    
    // Set alarm to trigger every 10ms (10000 microseconds), auto-reload
    timerAlarm(timer, 10000, true, 0);
    
    Serial.println("Hardware timer configured for 10ms interrupts");
    
  } 
  else 
  {
    Serial.println("\n*** WiFi Connection FAILED ***");
    Serial.println("Cannot send UDP packets without WiFi connection!");
    Serial.println("===================================");
  }
}

void loop() 
{
  static int counter = 0;

  // Wait for 10ms timer interrupt
  if (!timerFlag) 
  {
    return;  // Exit loop if timer hasn't triggered
  }
  
  timerFlag = false;  // Clear the flag

  // Only send if WiFi is connected
  if (WiFi.status() == WL_CONNECTED) 
  {
    // Check for incoming UDP messages
    checkIncomingUDP();
    
    //A pin state change has been detected.
    if (pinStateChanged23||pinStateChanged22) 
    {
      // Handle the pin change here
      if(pinStateChanged23)
      {
         Serial.println("Pin 23 changed!");
      }
      else if(pinStateChanged22)
      {
        Serial.println("Pin 22 changed!");
      }

      message = "H:5";
      pinStateChanged23 = false;
      pinStateChanged22 = false;

      // Send UDP packet
      udp.beginPacket(udpAddress, udpPortTX);
      udp.print(message);
      udp.endPacket();
    }
  }
}

void setBoxColor(Color color)
{
    // Get RGB values from colorMap
    RGBColor rgb = colorMap[color];
    
    // Set all pixels to the specified color
    for (int i = 0; i < LED_STRING_LENGTH; i++) 
    {
      pixels.setPixelColor(i, pixels.Color(rgb.red, rgb.green, rgb.blue));
    }
    pixels.show();
}

Color parseColorString(String colorStr)
{
    // Convert string to uppercase for comparison
    colorStr.toUpperCase();
    
    if (colorStr == "BLUE") return BLUE;
    if (colorStr == "GREEN") return GREEN;
    if (colorStr == "RED") return RED;
    
    return GREEN;  // Default to GREEN if unknown
}

void checkIncomingUDP()
{
    // Check if data is available
    int packetSize = udp.parsePacket();
    if (packetSize) 
    {
        // Read the incoming packet
        String incomingMessage = "";
        while (udp.available()) 
        {
            incomingMessage += (char)udp.read();
        }
        incomingMessage.trim();
        
        Serial.print("[RECEIVED] ");
        Serial.println(incomingMessage);
        
        // Parse format: boxNumber,colorName (e.g., "5,GREEN")
        int commaIndex = incomingMessage.indexOf(',');
        if (commaIndex != -1) 
        {
            String boxStr = incomingMessage.substring(0, commaIndex);
            String colorStr = incomingMessage.substring(commaIndex + 1);
            
            int boxNumber = boxStr.toInt();
            if(boxNumber == 5)
            {  
              Color color = parseColorString(colorStr);
              
              Serial.print("Box: ");
              Serial.print(boxNumber);
              Serial.print(", Color: ");
              Serial.println(colorStr);
              
              // Set the box color
              setBoxColor(color);
            }
        }
    }
}