#include <WiFi.h>
#include <WiFiUdp.h>

// WiFi credentials
const char* ssid = "OCEANWALK2";
const char* password = "ilovetom";  // Replace with your actual password

// UDP Configuration
const char* udpAddress = "192.168.0.173";  // IP address of computer running udp_controller.py
const int udpPort = 5007;  // Port where udp_controller.py is listening

WiFiUDP udp;
const int input_pin = 23;
const int pwm_pin = 22;
const int LEDC_CHANNEL = 0;
const int LEDC_FREQ = 38000;  // 38 kHz for IR control
const int LEDC_RESOLUTION = 10;  // 10-bit resolution (0-1023)

// Message variable
uint8_t message = 0;

// Interrupt variables
volatile bool pinStateChanged = false;
volatile unsigned long lastInterruptTime = 0;

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 1000;  // Send every 1 second (1000 ms)

// Interrupt Service Routine for pin 23
void IRAM_ATTR pin23ISR() 
{
    pinStateChanged = true;
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
  
  while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.println();
  
  // Check if connected
  if (WiFi.status() == WL_CONNECTED) {
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
    Serial.println(udpPort);
    Serial.println("===================================\n");
    
    // Initialize UDP
    udp.begin(udpPort);

    pinMode(input_pin, INPUT_PULLUP);
    
    // Attach interrupt to pin 23 (triggers on CHANGE - both rising and falling edges)
    attachInterrupt(digitalPinToInterrupt(input_pin), pin23ISR, RISING);

    Serial.println("Interrupt attached to pin 23");

    // Configure pin 22 for 38 kHz PWM output
    ledcAttach(pwm_pin, LEDC_FREQ, LEDC_RESOLUTION);
    ledcWrite(pwm_pin, 512);  // Set 50% duty cycle (512 out of 1023 for 10-bit)
    
    Serial.println("Pin 22 configured for 38 kHz PWM output");
    
  } else {
    Serial.println("\n*** WiFi Connection FAILED ***");
    Serial.println("Cannot send UDP packets without WiFi connection!");
    Serial.println("===================================");
  }
}

void loop() 
{
  // Only send if WiFi is connected
  if (WiFi.status() == WL_CONNECTED) 
  {

    if (pinStateChanged) 
    {
      pinStateChanged = false;  // Reset the flag
      // Handle the pin change here
      Serial.println("Pin 23 changed!");
      
      unsigned long currentTime = millis();
      message = 0x16;
      // Send UDP packet
      udp.beginPacket(udpAddress, udpPort);
      udp.print(message);
      udp.endPacket();
      
      // Print confirmation to serial monitor
      Serial.print("[SENT] ");
      Serial.print(message);
      Serial.print(" at ");
      Serial.print(currentTime / 1000.0, 3);
      Serial.println(" seconds");
    }
  }
   else 
  {
    // WiFi disconnected, try to reconnect
    Serial.println("WiFi disconnected! Attempting to reconnect...");
    WiFi.begin(ssid, password);
    delay(5000);
  }
}
