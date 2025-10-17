// https://roboticsbackend.com/arduino-fast-digitalwrite/ als Alternative
//#include <digitalWriteFast.h>


// PWM Pin
#define LASER_PIN_405 5
#define LASER_PIN_SUPERCON 4
#define LASER_PIN_445_KILL_SWITCH 8
#define LED_R_PIN 9
#define LED_G_PIN 10
#define LED_B_PIN 12                 // ich weiß nicht, wieso. Wahrscheinlich wegen der Register. Aber Pin 11 steuert die Brightness des 445 nm Lasers...
#define SERIAL_DATA_LENGTH 18        // ein Arduino long hat maximal 10 Ziffern. Plus die 6 für den Namen, ein für das = (6+1 Prefix also) und einen für den Null Characer
#define SERIAL_DATA_PREFIX_LENGTH 7  // SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH ist demnach die maximal mögliche Anzahl an Ziffern

// PWM-Signal zwischen 0-255
byte laser405Brightness = 0;
unsigned int laser445PulseNum = 0;
unsigned int laser445PulseDelay = -1;

#define LASER_PIN_445 3
// für 445 LASER nur manuelles PWM Signal setzen
#define MODE_SWICH_445 0

// https://github.com/bigjosh/TimerShot/blob/master/TimerShot.ino

#define OSP_SET_WIDTH(cycles) (OCR2B = 0xff - (cycles - 1))

// Setup the one-shot pulse generator and initialize with a pulse width that is (cycles) clock counts long

void osp_setup(uint8_t cycles) {


  TCCR2B = 0;  // Halt counter by setting clock select bits to 0 (No clock source).
               // This keeps anyhting from happeneing while we get set up

  TCNT2 = 0x00;           // Start counting at bottom.
  OCR2A = 0;              // Set TOP to 0. This effectively keeps us from counting becuase the counter just keeps reseting back to 0.
                          // We break out of this by manually setting the TCNT higher than 0, in which case it will count all the way up to MAX and then overflow back to 0 and get locked up again.
  OSP_SET_WIDTH(cycles);  // This also makes new OCR values get loaded frm the buffer on every clock cycle.

  TCCR2A = _BV(COM2B0) | _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);  // OC2B=Set on Match, clear on BOTTOM. Mode 7 Fast PWM.
  TCCR2B = _BV(WGM22) | _BV(CS20);                               // Start counting now. WGM22=1 to select Fast PWM mode 7

  DDRD |= _BV(3);  // Set pin to output (Note that OC2B = GPIO port PD3 = Arduino Digital Pin 3)
}

// Setup the one-shot pulse generator

void osp_setup() {

  osp_setup(laser445PulseNum);
}

// Fire a one-shot pulse. Use the most recently set width.

#define OSP_FIRE() (TCNT2 = OCR2B - 1)

// Test there is currently a pulse still in progress

#define OSP_INPROGRESS() (TCNT2 > 0)

// Fire a one-shot pusle with the specififed width.
// Order of operations in calculating m must avoid overflow of the unint8_t.
// TCNT2 starts one count lower than the match value becuase the chip will block any compare on the cycle after setting a TCNT.

#define OSP_SET_AND_FIRE(cycles) \
  { \
    uint8_t m = 0xff - (cycles - 1); \
    OCR2B = m; \
    TCNT2 = m - 1; \
  }


// 0: Laser aus
// 1: Laser an
// 2: Es wird auf Daten zum setzen von Parametern gewartet.
char mode = 'z';
bool modeChanged = false;

// default
bool continuousMeasurement = true;
// Timeout zum Abschalten der Laser (wenn das Timeout verstrichen ist, wird angenommen, dass die Verbindung zur Steuersoftware unterbrochen wurde und kein laserOff Signal mehr empfangen werden kann)
unsigned long expectedDelay = 0;
unsigned long lastUpdateTime = 0;

void setup() {

  pinMode(LED_R_PIN, OUTPUT);
  pinMode(LED_G_PIN, OUTPUT);
  pinMode(LED_B_PIN, OUTPUT);

  pinMode(LASER_PIN_SUPERCON, OUTPUT);
  pinMode(LASER_PIN_445_KILL_SWITCH, OUTPUT);
  pinMode(LASER_PIN_405, OUTPUT);

  pinMode(LASER_PIN_445, OUTPUT);

  enableLocks();
  // die default 115200 überschreiben, die von der Library gesetzt werden.
  // ansonsten gehen bei Processing Werte verloren.
  Serial.begin(9600);  //115200

  // // Phase-Correct PWM with duty cicle 1 over 255 https://docs.arduino.cc/tutorials/generic/secrets-of-arduino-pwm/
  // pinMode(3, OUTPUT);
  // pinMode(11, OUTPUT);
  // TCCR2A = _BV(COM2A1) | _BV(COM2B1) | _BV(WGM20);
  // TCCR2B = _BV(CS22);
  // OCR2A = 1;
  // OCR2B = 1;

  if (!MODE_SWICH_445)
    osp_setup();
}

void loop() {
  // disableLocks();
  // laser445PulseNum = 50;
  // osp_setup();

  // while (true) {
  //   //OSP_SET_AND_FIRE(5);
  //   OSP_FIRE();

  //   while (OSP_INPROGRESS())
  //     ;  // This just shows how you would wait if nessisary - not nessisary in this application.

  //   // analogWrite(11, 40);  // 30
  //   delay(20);
  // }
  readSerial();
}


char varSerialData[SERIAL_DATA_LENGTH];
// the name of the value consists of the first 6 chars
char varNameData[SERIAL_DATA_PREFIX_LENGTH];
char varValueData[SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH];

/*
  Kann auch mit Serial benutzt werden:

  PWM405=<value>
  Del445=<value>
  Num445=<value>
  SetLED=<value> // drei Ziffern, stehehnd für RGB. 1 ist 0, 2 ist 1 usw.
*/

void readSerial() {

  if (!modeChanged) {
    if (Serial.available() == 0)
      return;

    // // ist fünf schon zu viel?? Länge mal ausgeben lassen
    // byte m = Serial.readBytesUntil('\n', varSerialData, 15);
    // // clear buffer
    // // while (Serial.available() > 0)
    // //   Serial.read();

    // varSerialData[m] = '\0';
    // // Serial.println(varSerialData);

    char newMode = Serial.read();
    // Serial.println(newMode);


    // update (bei einem continuousMeasurement)
    if (continuousMeasurement && newMode == '3') {
      lastUpdateTime = millis();
      return;
    }

    // es kann mehrmals nacheinander eine Variable gesetzt werden
    if (newMode != mode || (mode == '2' && newMode == '2')) {
      mode = newMode;
      modeChanged = true;
    }
    return;
  }

  // reset
  modeChanged = false;

  switch (mode) {

    case '0':
      turnLasersOff();
      break;

    case '1':
      lastUpdateTime = millis();
      turnLasersOn();
      // Serial.println("turned on!");
      break;

    case '2':
      byte m = Serial.readBytesUntil('\n', varSerialData, SERIAL_DATA_LENGTH);

      if (m < 6)
        return;

      // add '\0'
      varSerialData[m] = '\0';
      // Serial.println(varSerialData);

      varNameData[SERIAL_DATA_PREFIX_LENGTH - 1] = '\0';
      for (int i = 0; i < SERIAL_DATA_PREFIX_LENGTH - 1; i++) {
        varNameData[i] = varSerialData[i];
      }

      // // remove the name in the array
      // memset(varSerialData, 0x30, SERIAL_DATA_PREFIX_LENGTH);
      for (int i = 0; i < SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH - 1; i++) {
        varValueData[i] = varSerialData[SERIAL_DATA_PREFIX_LENGTH + i];
      }

      if (strcmp(varNameData, "PWM405") == 0) {
        laser405Brightness = atoi(varValueData);
        // Serial.println("Setting laser405Brightness");
        // Serial.println(laser405Brightness, DEC);
      } else if (strcmp(varNameData, "Del445") == 0) {
        laser445PulseDelay = atoi(varValueData);
        // Serial.println("Setting laser445PulseDelay");
        // Serial.println(laser445PulseDelay, DEC);
      } else if (strcmp(varNameData, "Num445") == 0) {
        laser445PulseNum = atoi(varValueData);
        if (!MODE_SWICH_445)
          osp_setup();
        // Serial.println("Setting laser445PulseNum");
        // Serial.println(laser445PulseNum, DEC);
      } else if (strcmp(varNameData, "SetLED") == 0) {
        String data = (String)atoi(varValueData);  // z. B. 0000000222 zu 222
        // Serial.println(data);
        int r = data[0] - '0';
        int g = data[1] - '0';
        int b = data[2] - '0';
        // 1 ist Null, weil sonst 002 zu 2 werden würde statt 002 (es soll sehr simpel sein)
        setLED((r - 1) * 10, (g - 1) * 10, (b - 1) * 10);
      } else if (strcmp(varNameData, "ConMea") == 0) {
        continuousMeasurement = atoi(varValueData);
        // Serial.println("Setting continuousMeasurement");
        // Serial.println(continuousMeasurement);
      } else if (strcmp(varNameData, "ExpDel") == 0) {
        expectedDelay = atol(varValueData);
        // Serial.println("Setting expectedDelay");
        // Serial.println(varValueData);
        // Serial.println(expectedDelay);
      }
      // reset array
      memset(varSerialData, 0x00, SERIAL_DATA_LENGTH);
      memset(varNameData, 0x00, SERIAL_DATA_PREFIX_LENGTH);
      memset(varValueData, 0x00, SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH);

      break;
  }
}

void setLED(byte r, byte g, byte b) {

  // Serial.println("setting LED" + String(r));
  analogWrite(LED_R_PIN, r);
  analogWrite(LED_G_PIN, g);
  analogWrite(LED_B_PIN, b);
}

void enableLocks() {

  digitalWrite(LASER_PIN_445_KILL_SWITCH, LOW);
  digitalWrite(LASER_PIN_SUPERCON, HIGH);
  analogWrite(LASER_PIN_405, 0);
}

void disableLocks() {

  digitalWrite(LASER_PIN_445_KILL_SWITCH, HIGH);
}

void turnLasersOn() {

  disableLocks();
  analogWrite(LASER_PIN_405, laser405Brightness);
  // Serial.println("brightness: " + String(laser405Brightness));
  digitalWrite(LASER_PIN_SUPERCON, LOW);

  while (true) {

    if (laser445PulseNum == 1234 || MODE_SWICH_445) {
      // TCCR2B = 0;
      // LOW, HIGH, bringt alles nix
      digitalWrite(LASER_PIN_445, HIGH);
      //analogWrite(LASER_PIN_445, 255);
    } else {

      // You could wrap OSP_SET_AND_FIRE(o); in a non-blocking millis()-guarded loop to set the frequency to whatever you want.
      OSP_FIRE();

      while (OSP_INPROGRESS())
        ;  // This just shows how you would wait if nessisary - not nessisary in this application.

      delay(laser445PulseDelay);
    }
    readSerial();
    if (millis() - lastUpdateTime >= expectedDelay) {
      mode = '0';
    }
    if (mode != '1') {
      turnLasersOff();
      break;
    }
  }
}

void turnLasersOff() {
  enableLocks();
  lastUpdateTime = millis();
}
