#include <Adafruit_NeoPixel.h>

#define LED_STRING_LENGTH 47
#define LED_PIN 8


Adafruit_NeoPixel square_LED = Adafruit_NeoPixel(LED_STRING_LENGTH,LED_PIN);

// Configure Timer 1 for 38kHz PWM on pin 9 (50% duty cycle)
void setup_38kHz_PWM() {
  pinMode(9, OUTPUT);
  
  // Set Timer 1 to Fast PWM mode 14 (WGM13:0 = 1110), non-inverting
  TCCR1A = _BV(COM1A1) | _BV(WGM11);  // Non-inverting PWM on OC1A
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS10);  // Fast PWM mode 14, no prescaler
  
  // 38kHz = 16MHz / (1 + ICR1) → ICR1 = 420
  ICR1 = 420;   // TOP value for 38.005 kHz
  OCR1A = 210;  // 50% duty cycle
}

void setup() {
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  pinMode(A5, OUTPUT);
  pinMode(LED_PIN,OUTPUT);
  Serial.begin(115200);
  
  // Generate 38kHz on pin 9 using hardware PWM
  setup_38kHz_PWM();
  square_LED.begin();
}

void loop() 
{
  int ball_sensed = false;
  static int counter_value = 0; 
  int value =  digitalRead(A0);
  int value2 = digitalRead(A1);
  static int ball_prev_sens = false;
  
     
  if(value || value2)
  {
     ball_sensed = true;
     counter_value = 500;
  }

  if(counter_value)
  {
    digitalWrite(A5,HIGH);
    counter_value--;
    
    if(counter_value == 1)
    {
      for(int n = 0; n <= LED_STRING_LENGTH ; n++)
      {
        square_LED.setPixelColor(n,square_LED.Color(0,255,0));
      }

      square_LED.show();
    }
  }
  else
  {
    digitalWrite(A5,LOW);
  }

  //Check for rising edge of ball sense
  if (ball_sensed && !ball_prev_sens) 
  {
      // Rising edge detected
      for(int n = 0; n <= LED_STRING_LENGTH ; n++)
      {
        square_LED.setPixelColor(n,square_LED.Color(50,50,255));
      }

      square_LED.show();
  }

  ball_prev_sens = ball_sensed;
}
