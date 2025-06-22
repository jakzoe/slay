#include <Arduino.h>

// UART1 nutzen (gibt kein UART2 bei C3)
HardwareSerial LaserSerial(1);

// ESP32-C3 haben 6 channels (https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html)
// Pins, die einen Channel teilen, teilen automatisch das generierte PWM-Signal
// C3 hat nur slow speed mode
#define PWM_CHANNEL_405 0
uint16_t pwmFreq405 = 2000; // 80_000_000 / 2**14 = 4882.8125, aber ab 4.5 kHz geht nichts mehr. Vermutlich macht da das MOSFET nicht mehr mit.
// geht theoretisch bis 14, dann funktioniert es aber ab ca. 75 Prozent Duty nicht mehr.
// (zumindest bei dem 405 nm Laser sind zwar bei dem TTL-Eingang auch 14 bit möglich,
// bei einer direkten Steuerung des Stroms mittels eines MOSFETs aber nicht. Ggf. liegt das auch an dem MOSFET IRF510N)
uint8_t pwmResBits405 = 13;
uint16_t maxDutyVal405 = (uint16_t)(pow(2, pwmResBits405) - 1);
uint16_t pwmDutyVal405 = 0;

#define PWM_CHANNEL_445 4
uint16_t pwmFreq445 = 2000;
uint8_t pwmResBits445 = 13;
uint16_t maxDutyVal445 = (uint16_t)(pow(2, pwmResBits445) - 1);
uint16_t pwmDutyVal445 = 0;

#define PWM_CHANNEL_NITRO 2
// in us (2-60 sind möglich. Höhere Werte sind einfacher für das PWM)
// Höhere Werte scheinen dennoch ebenfalls zu funktionieren.
#define PULSE_WIDTH_NITRO 55
// Laser kann bis zu 60 Hz. Höher geht dennoch, das wird dann vom Laser selbstständg auf 60 Hz geregelt.
uint8_t pwmFreqNitro = 10;
// (konstant, da es keinen Grund gibt, die PWM-Auflösung zu ändern)
// Für < 14 wird der Ausdruck von getLTButyVal() zu klein.
#define PWM_RES_BITS_NITRO 14
uint16_t MAX_DUTY_VAL_NITRO = (uint16_t)(pow(2, PWM_RES_BITS_NITRO) - 1);

// PWM Pin
#define LASER_PIN_405 8
#define LASER_PIN_445 2
#define LASER_PIN_NITROGEN 7

// wenn der 445 nm Laser kein PWM erhält, erreicht er die maximale Leistung.
#define DISABLE_PWM_445 false
#define LASER_PIN_SUPERCON 10
#define LASER_PIN_445_KILL_SWITCH 9
#define RElAY_405 3
#define RElAY_445 1
// nicht genug pins. Daher entweder Relays oder LED benutzen
#define USE_RGB_LED false
#define LED_R_PIN 1
#define LED_G_PIN 3
#define LED_B_PIN 1 // blue disablen (zu wenig Pins)
// ein Arduino long hat maximal 10 Ziffern. Plus die 6 für den Namen, ein für das = (6+1 Prefix also) und einen für den Null Characer
#define SERIAL_DATA_LENGTH 18
// SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH ist demnach die maximal mögliche Anzahl an Ziffern
#define SERIAL_DATA_PREFIX_LENGTH 7
#define POT_PIN 0
#define POTI_SAMPLE_COUNT 51
int potiReadings[POTI_SAMPLE_COUNT];

// 0: Laser aus
// 1: Laser an
// 2: Es wird auf Daten zum setzen von Parametern gewartet.
// 3: watchdog updaten (like a dead man's switch press)
char mode = 'z'; // random init value
bool modeChanged = false;

// default
bool continuousMeasurement = true;
// Timeout zum Abschalten der Laser
// (wenn das Timeout verstrichen ist, wird angenommen, dass die Verbindung zur Steuersoftware unterbrochen wurde und kein laserOff Signal mehr empfangen werden kann)
unsigned long expectedDelay = 0;
unsigned long lastUpdateTime = 0;

bool lasersAreOn = false;

void readSerial();
void setLED(byte r, byte g, byte b);
void enableLocks();
void disableLocks();
void turnLasersOn();
void turnLasersOff();
uint16_t readPoti();
uint16_t getLTBDutyVal();

void setup()
{

  // input voltage rangem, ADC_11db ist 0-3.3 V (halt ESP32 Pin)
  analogSetAttenuation(ADC_11db);
  pinMode(POT_PIN, INPUT);

  if (USE_RGB_LED)
  {
    pinMode(LED_R_PIN, OUTPUT);
    pinMode(LED_G_PIN, OUTPUT);
    pinMode(LED_B_PIN, OUTPUT);
  }
  else
  {
    pinMode(RElAY_405, OUTPUT);
    pinMode(RElAY_445, OUTPUT);
    // die Relays sind active low
    digitalWrite(RElAY_405, LOW);
    digitalWrite(RElAY_445, LOW);
  }

  pinMode(LASER_PIN_SUPERCON, OUTPUT);
  pinMode(LASER_PIN_NITROGEN, OUTPUT);
  pinMode(LASER_PIN_445_KILL_SWITCH, OUTPUT);
  pinMode(LASER_PIN_405, OUTPUT);
  pinMode(LASER_PIN_445, OUTPUT);

  if (!DISABLE_PWM_445)
  {
    ledcAttachChannel(LASER_PIN_445, pwmFreq445, pwmResBits445, PWM_CHANNEL_445);
  }

  ledcAttachChannel(LASER_PIN_405, pwmFreq405, pwmResBits405, PWM_CHANNEL_405);
  // pull up
  // ledcOutputInvert(LASER_PIN_NITROGEN, true);
  ledcAttachChannel(LASER_PIN_NITROGEN, pwmFreqNitro, PWM_RES_BITS_NITRO, PWM_CHANNEL_NITRO);

  // ledcAttachChannel attached die Pins auch, daher direkt ausschalten
  enableLocks();

  // Serial.begin(115200);

  // UART0 ist beim Debugging nicht verfügbar. Daher UART1 für simultanes Serial benutzen.
  // Dazu die default pins 20 und 21 von UART0 detachen (automatisch) und an UART1 attachen.
  // (andere Pins gingen auch, aber 20 und 21 können sowieso weder PWM, noch sind sie analoge Pins etc.)

  // Serial.end(); // müsste es selbst tun
  // use default 8 bits 1 stop bit, no parity
  LaserSerial.begin(115200, SERIAL_8N1, 20, 21);
  LaserSerial.flush();

  // TEST
  // turnLasersOn();
  // turnLasersOff();
}

void loop()
{

  // disableLocks();
  readSerial();

  // return;
  // watchdog
  if (lasersAreOn && millis() - lastUpdateTime >= expectedDelay)
  {
    turnLasersOff();
    mode = '0';
  }
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

void readSerial()
{

  if (!modeChanged)
  {
    if (LaserSerial.available() == 0)
      return;

    // // ist fünf schon zu viel?? Länge mal ausgeben lassen
    // byte m = LaserSerial.readBytesUntil('\n', varSerialData, 15);
    // // clear buffer
    // // while (LaserSerial.available() > 0)
    // //   LaserSerial.read();

    // varSerialData[m] = '\0';
    // // LaserSerial.println(varSerialData);

    char newMode = LaserSerial.read();
    // LaserSerial.println(newMode);

    // update (bei einem continuousMeasurement)
    if (continuousMeasurement && newMode == '3')
    {
      lastUpdateTime = millis();
      return;
    }

    // es könnte mehrmals nacheinander eine Variable gesetzt werden
    if (newMode != mode || (mode == '2' && newMode == '2'))
    {
      mode = newMode;
      modeChanged = true;
    }
    return;
  }

  // reset
  modeChanged = false;

  switch (mode)
  {

  case '0':
    turnLasersOff();
    break;

  case '1':
    lastUpdateTime = millis();
    turnLasersOn();
    // LaserSerial.println("turned on!");
    break;

  case '2':
    byte m = LaserSerial.readBytesUntil('\n', varSerialData, SERIAL_DATA_LENGTH);

    if (m <= SERIAL_DATA_PREFIX_LENGTH)
      return;

    // add '\0'
    varSerialData[m] = '\0';
    // LaserSerial.println(varSerialData);

    // replace equal sign with null character
    varNameData[SERIAL_DATA_PREFIX_LENGTH - 1] = '\0';
    for (int i = 0; i < SERIAL_DATA_PREFIX_LENGTH - 1; i++)
    {
      varNameData[i] = varSerialData[i];
    }

    // // remove prefix
    // memset(varSerialData, 0x30, SERIAL_DATA_PREFIX_LENGTH);
    for (int i = 0; i < SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH - 1; i++)
    {
      varValueData[i] = varSerialData[SERIAL_DATA_PREFIX_LENGTH + i];
    }

    if (strcmp(varNameData, "Dut405") == 0)
    {
      pwmDutyVal405 = atoi(varValueData);
      ledcWrite(LASER_PIN_405, pwmDutyVal405);
      // LaserSerial.println("Setting pwmDutyVal405");
      // LaserSerial.println(pwmDutyVal405, DEC);
    }
    else if (strcmp(varNameData, "Dut445") == 0)
    {
      pwmDutyVal445 = atoi(varValueData);
      if (!DISABLE_PWM_445)
      {
        ledcWrite(LASER_PIN_445, pwmDutyVal445);
      }
      // LaserSerial.println("Setting pwmDutyVal445");
      // LaserSerial.println(pwmDutyVal445, DEC);
    }
    else if (strcmp(varNameData, "Frq405") == 0)
    {
      pwmFreq405 = atoi(varValueData);

      ledcChangeFrequency(LASER_PIN_405, pwmFreq405, pwmResBits405);
      // LaserSerial.println("Setting pwmFreq405");
      // LaserSerial.println(pwmFreq405, DEC);
    }
    else if (strcmp(varNameData, "Frq445") == 0)
    {
      pwmFreq445 = atoi(varValueData);
      if (!DISABLE_PWM_445)
      {
        ledcChangeFrequency(LASER_PIN_445, pwmFreq445, pwmResBits445);
      }
      // LaserSerial.println("Setting pwmFreq445");
      // LaserSerial.println(pwmFreq445, DEC);
    }
    else if (strcmp(varNameData, "Res405") == 0)
    {
      pwmResBits405 = atoi(varValueData);

      // update
      maxDutyVal405 = (uint16_t)(pow(2, pwmResBits405) - 1);

      ledcChangeFrequency(LASER_PIN_405, pwmFreq405, pwmResBits405);

      // LaserSerial.println("Setting pwmResBits405");
      // LaserSerial.println(pwmResBits405, DEC);
    }
    else if (strcmp(varNameData, "Res445") == 0)
    {
      pwmResBits445 = atoi(varValueData);
      // update
      maxDutyVal445 = (uint16_t)(pow(2, pwmResBits445) - 1);

      if (!DISABLE_PWM_445)
      {
        ledcChangeFrequency(LASER_PIN_445, pwmFreq445, pwmResBits445);
      }
      // LaserSerial.println("Setting pwmResBits445");
      // LaserSerial.println(pwmResBits445, DEC);
    }
    else if (strcmp(varNameData, "FrqLTB") == 0)
    {
      pwmFreqNitro = atoi(varValueData);
      ledcChangeFrequency(LASER_PIN_NITROGEN, pwmFreqNitro, PWM_RES_BITS_NITRO);
      // LaserSerial.println("Setting pwmFreqNitro");
      // LaserSerial.println(pwmFreqNitro, DEC);
    }
    else if (strcmp(varNameData, "SetLED") == 0)
    {
      String data = (String)atoi(varValueData); // z. B. 0000000222 zu 222
      // LaserSerial.println(data);
      int r = data[0] - '0';
      int g = data[1] - '0';
      int b = data[2] - '0';
      // 1 ist Null, weil sonst 002 zu 2 werden würde statt 002 (es soll sehr simpel sein)
      setLED((r - 1) * 10, (g - 1) * 10, (b - 1) * 10);
    }
    else if (strcmp(varNameData, "ConMea") == 0)
    {
      continuousMeasurement = atoi(varValueData);
      // LaserSerial.println("Setting continuousMeasurement");
      // LaserSerial.println(continuousMeasurement);
    }
    else if (strcmp(varNameData, "ExpDel") == 0)
    {
      expectedDelay = atol(varValueData);
      // LaserSerial.println("Setting expectedDelay");
      // LaserSerial.println(varValueData);
      // LaserSerial.println(expectedDelay);
    }
    // reset array
    memset(varSerialData, 0x00, SERIAL_DATA_LENGTH);
    memset(varNameData, 0x00, SERIAL_DATA_PREFIX_LENGTH);
    memset(varValueData, 0x00, SERIAL_DATA_LENGTH - SERIAL_DATA_PREFIX_LENGTH);

    break;
  }
}

void setLED(byte r, byte g, byte b)
{

  if (!USE_RGB_LED)
    return;

  // LaserSerial.println("setting LED" + String(r));
  analogWrite(LED_R_PIN, r);
  analogWrite(LED_G_PIN, g);
  analogWrite(LED_B_PIN, b);
}

void enableLocks()
{

  digitalWrite(LASER_PIN_445_KILL_SWITCH, LOW);
  pinMode(LASER_PIN_445_KILL_SWITCH, OUTPUT);
  digitalWrite(LASER_PIN_SUPERCON, HIGH);

  // nur den duty cycle auf 0 setzen würde vermutlich dazu führen, dass es beim Resetten des PWM-Timers einen voltage-spike von einem Clock-Cycle gibt.
  ledcDetach(LASER_PIN_405);
  pinMode(LASER_PIN_405, OUTPUT);
  digitalWrite(LASER_PIN_405, LOW);

  ledcDetach(LASER_PIN_445);
  pinMode(LASER_PIN_445, OUTPUT);
  digitalWrite(LASER_PIN_445, LOW);

  ledcDetach(LASER_PIN_NITROGEN);
  pinMode(LASER_PIN_NITROGEN, OUTPUT);
  digitalWrite(LASER_PIN_NITROGEN, LOW);
}

void disableLocks()
{
  digitalWrite(LASER_PIN_445_KILL_SWITCH, HIGH);
}

void turnLasersOn()
{

  lasersAreOn = true;
  disableLocks();

  ledcAttachChannel(LASER_PIN_405, pwmFreq405, pwmResBits405, PWM_CHANNEL_405);
  ledcAttachChannel(LASER_PIN_445, pwmFreq445, pwmResBits445, PWM_CHANNEL_445);
  ledcAttachChannel(LASER_PIN_NITROGEN, pwmFreqNitro, PWM_RES_BITS_NITRO, PWM_CHANNEL_NITRO);

  ledcWrite(LASER_PIN_405, pwmDutyVal405);
  ledcWrite(LASER_PIN_NITROGEN, getLTBDutyVal());
  // pull-up resistor, thus inverted logic
  digitalWrite(LASER_PIN_SUPERCON, LOW);

  if (pwmDutyVal445 == 1234 || DISABLE_PWM_445)
  {
    // LOW, HIGH, bringt alles nix
    digitalWrite(LASER_PIN_445, HIGH);
  }
  else
  {
    ledcWrite(LASER_PIN_445, pwmDutyVal445);
  }
}

void turnLasersOff()
{
  enableLocks();
  lastUpdateTime = millis();
  lasersAreOn = false;
}

uint16_t getLTBDutyVal()
{
  return (PULSE_WIDTH_NITRO * MAX_DUTY_VAL_NITRO) / (1000000 / pwmFreqNitro);
}

// median filter
uint16_t readPoti()
{
  for (int i = 0; i < POTI_SAMPLE_COUNT; i++)
  {
    potiReadings[i] = analogRead(POT_PIN);
    delay(2);
  }

  for (int i = 0; i < POTI_SAMPLE_COUNT - 1; i++)
  {
    for (int j = i + 1; j < POTI_SAMPLE_COUNT; j++)
    {
      if (potiReadings[j] < potiReadings[i])
      {
        int temp = potiReadings[i];
        potiReadings[i] = potiReadings[j];
        potiReadings[j] = temp;
      }
    }
  }

  return potiReadings[POTI_SAMPLE_COUNT / 2];
}