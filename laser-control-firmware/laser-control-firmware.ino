#include <Debug.h>
#include "DEV_Config.h"
#include "Waveshare_AS7341.h"

// https://roboticsbackend.com/arduino-fast-digitalwrite/ als Alternative
//#include <digitalWriteFast.h>

#define SENSOR_TRIGGER_PIN 7
// PWM Pin
#define LASER_PIN_445 6
// PWM Pin
#define LASER_PIN_405 5
#define LASER_PIN_SUPERCON 4

unsigned long superconTime = 0;
unsigned int superconPeriod = 200;
unsigned int superconDuration = 100;

// PWM-Signal zwischen 0-255
byte laser445Brightness = 255;
// PWM-Signal zwischen 0-255
byte laser405Brightness = 255;

void setup() {

  DEV_ModuleInit();
  AS7341_Init(eSyns);
  // approximately ATIME*ASTEP*2.8 µs is the intergration time
  AS7341_ATIME_config(3);
  AS7341_ASTEP_config(100);
  AS7341_AGAIN_config(5);

  pinMode(SENSOR_TRIGGER_PIN, OUTPUT);
  digitalWrite(SENSOR_TRIGGER_PIN, HIGH);

  pinMode(LASER_PIN_SUPERCON, OUTPUT);
  digitalWrite(LASER_PIN_SUPERCON, HIGH);

  pinMode(LASER_PIN_445, OUTPUT);
  analogWrite(LASER_PIN_445, 0);

  pinMode(LASER_PIN_405, OUTPUT);
  analogWrite(LASER_PIN_405, 0);
  // die default 115200 überschreiben, die von der Library gesetzt werden.
  // ansonsten gehen bei Processing Werte verloren.
  Serial.begin(9600);  //115200
}

void loop() {

  // externalTriggerLaser('0');
  // delay(1000);
  // externalTriggerLaser('1');
  // delay(1000);
  //triggerLaser();
  readSerial();
}

void triggerLaser() {

  // trigger laser
  if (millis() - superconTime > superconPeriod) {
    // start laser-impuls
    superconTime = millis();

    // read data1
    AS7341_startMeasure(eF1F4ClearNIR);
    delay(10);
    while (!AS7341_MeasureComplete()) {

      analogWrite(LASER_PIN_445, laser445Brightness);
      analogWrite(LASER_PIN_405, laser405Brightness);

      digitalWrite(LASER_PIN_SUPERCON, LOW);
      digitalWrite(SENSOR_TRIGGER_PIN, LOW);

      delay(superconDuration);
      Serial.println("trigered");

      analogWrite(LASER_PIN_445, 0);
      analogWrite(LASER_PIN_405, 0);

      digitalWrite(LASER_PIN_SUPERCON, HIGH);
      digitalWrite(SENSOR_TRIGGER_PIN, HIGH);
    }
    //printSensorDataPlotter(AS7341_ReadSpectralDataOne());
    printSensorData(AS7341_ReadSpectralDataOne());

    // read data2
    AS7341_startMeasure(eF5F8ClearNIR);
    delay(10);
    while (!AS7341_MeasureComplete()) {

      analogWrite(LASER_PIN_445, laser445Brightness);
      analogWrite(LASER_PIN_405, laser405Brightness);

      digitalWrite(LASER_PIN_SUPERCON, LOW);
      digitalWrite(SENSOR_TRIGGER_PIN, LOW);

      delay(superconDuration);

      analogWrite(LASER_PIN_445, 0);
      analogWrite(LASER_PIN_405, 0);

      digitalWrite(LASER_PIN_SUPERCON, HIGH);
      digitalWrite(SENSOR_TRIGGER_PIN, HIGH);
    }
    //printSensorDataPlotter(AS7341_ReadSpectralDataTwo());
    printSensorData(AS7341_ReadSpectralDataTwo());
  }
}

void externalTriggerLaser(char charState) {

  switch (charState) {

    case '0':

      // schneller als digitalWriteFast-Library
      turnLasersOff();
      break;

      // // analogWrite(LASER_PIN_445, 0);
      // // analogWrite(LASER_PIN_405, 0);
      // digitalWriteFast(LASER_PIN_445, LOW);
      // digitalWriteFast(LASER_PIN_405, LOW);

      // //digitalWrite(LASER_PIN_SUPERCON, HIGH);
      // digitalWriteFast(LASER_PIN_SUPERCON, HIGH);
      // //Serial.println("turned off");
      // break;

    case '1':

      // schneller als digitalWriteFast-Library
      // ACHTUNG: ignoriert laser405Brightness und laser445Brightness, setzt direkt auf 255
      turnLasersOn();
      break;

      // // ähnlich wie in https://github.com/arduino/ArduinoCore-avr/blob/master/cores/arduino/wiring_analog.c:
      // if (laser445Brightness == 255 && laser405Brightness == 255) {
      //   digitalWriteFast(LASER_PIN_445, HIGH);
      //   digitalWriteFast(LASER_PIN_405, HIGH);
      // } else {
      //   analogWrite(LASER_PIN_445, laser445Brightness);
      //   analogWrite(LASER_PIN_405, laser405Brightness);
      // }
      // //digitalWrite(LASER_PIN_SUPERCON, LOW);
      // digitalWriteFast(LASER_PIN_SUPERCON, LOW);
      // //Serial.println("turned on");
      // break;
  }
}


void printSensorDataPlotter(sModeOneData_t data1) {

  Serial.print(data1.channel1);
  Serial.print(" ");
  Serial.print(data1.channel2);
  Serial.print(" ");
  Serial.print(data1.channel3);
  Serial.print(" ");
  Serial.print(data1.channel4);
  Serial.print(" ");
  //Serial.print(data1.CLEAR);
  //Serial.print(data1.NIR);
}

void printSensorDataPlotter(sModeTwoData_t data2) {

  Serial.print(data2.channel5);
  Serial.print(" ");
  Serial.print(data2.channel6);
  Serial.print(" ");
  Serial.print(data2.channel7);
  Serial.print(" ");
  Serial.println(data2.channel8);
  //Serial.println(data2.CLEAR);
  //Serial.println(data2.NIR);
}

void printSensorData(sModeOneData_t data1) {

  Serial.print("(405-425nm) ");
  Serial.println(data1.channel1);
  Serial.print("(435-455nm) ");
  Serial.println(data1.channel2);
  Serial.print("(470-490nm) ");
  Serial.println(data1.channel3);
  Serial.print("(505-525nm) ");
  Serial.println(data1.channel4);
  // Serial.print("Clear:");
  // Serial.println(data1.CLEAR);
  // Serial.print("NIR:");
  // Serial.println(data1.NIR);
}

void printSensorData(sModeTwoData_t data2) {

  Serial.print("(545-565nm) ");
  Serial.println(data2.channel5);
  Serial.print("(580-600nm) ");
  Serial.println(data2.channel6);
  Serial.print("(620-640nm) ");
  Serial.println(data2.channel7);
  Serial.print("(670-690nm) ");
  Serial.println(data2.channel8);
  Serial.print("Clear ");
  Serial.println(data2.CLEAR);
  Serial.print("NIR ");
  Serial.println(data2.NIR);
}

//char serialData[15];
char serialData[5];

/*
  Usage:

  PWM445=<value>
  PWM405=<value>
  supDur=<value>
*/
void readSerial() {

  if (Serial.available() == 0)
    return;

  //  byte m = Serial.readBytesUntil('\n', serialData, 15);
  byte m = Serial.readBytesUntil('\n', serialData, 5);
  // Serial.println(serialData);
  // Serial.println(serialData[0]);
  // Serial.println(int(serialData[0]));


  externalTriggerLaser(serialData[0]);
  // clear buffer
  // while (Serial.available() > 0)
  //   Serial.read();
  return;
  //int m = 0;

  if (m < 6)
    return;

  // add '\0'
  serialData[m] = '\0';
  Serial.println(serialData);

  // the name of the value consists of the first 6 chars
  char name[7];
  name[6] = '\0';
  for (int i = 0; i < 6; i++) {
    name[i] = serialData[i];
  }

  // remove the name in the array
  Serial.println(serialData);
  memset(serialData, 0x30, 7);
  Serial.println(serialData);


  if (strcmp(name, "PWM445")) {
    laser445Brightness = atoi(serialData);
    Serial.println(laser445Brightness, DEC);
    // reset array
    memset(serialData, 0x00, 15);

  } else if (strcmp(name, "PWM405")) {
    laser405Brightness = atoi(serialData);
    Serial.println(laser405Brightness, DEC);
    // reset array
    memset(serialData, 0x00, 15);

  } else if (strcmp(name, "supDur")) {
    superconDuration = atol(serialData);
    Serial.println(superconDuration, DEC);
    // reset array
    memset(serialData, 0x00, 15);
  }
}

// funktioniert nur für Arduino Uno (Unterschiede je nach Pin-Layout)

void turnLasersOn() {
  PORTD = B01100000;
}

void turnLasersOff() {
  PORTD = B10010000;
}

// für Arduino-Uno: digitale Pins von 0-7 sind D, 8-13 B, analoge Pins C
// https://roboticsbackend.com/arduino-uno-pins-a-complete-practical-guide/

// alle Pins auf LOW setzen, pinNumber auf HIGH
void digitalWriteFastAnalogHigh(byte pinNumber) {

  PORTC = 0;
  PORTC |= (1 << pinNumber);
}
