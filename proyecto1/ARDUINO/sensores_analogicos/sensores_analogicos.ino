


const byte TRIG = 7;
const byte ECHO = 8;
const byte VENTILADOR = 9;
unsigned long ultimoControl = 0;

void setup() {
  digitalWrite(VENTILADOR, LOW);
  pinMode(VENTILADOR, OUTPUT);
  Serial.begin(9600);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  digitalWrite(TRIG, LOW);
}

void loop() {

  if (millis() - ultimoControl > 10000UL) digitalWrite(VENTILADOR, LOW);
  if (Serial.available() == 0) return;
  char comando = Serial.read();
  if (comando == 'F' || comando == 'f') {
    digitalWrite(VENTILADOR, comando == 'F' ? HIGH : LOW);
    ultimoControl = millis();
    return;
  }
  if (comando == 'L') {
    analogRead(A0);
    int gas = analogRead(A0);
    analogRead(A1);
    int luz = analogRead(A1);
    digitalWrite(TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG, LOW);
    unsigned long duracion = pulseIn(ECHO, HIGH, 30000UL);
    float distancia = duracion * 0.0343f / 2.0f;
    Serial.print("{\"gas\":");
    Serial.print(gas);
    Serial.print(",\"luz_adc\":");
    Serial.print(luz);
    Serial.print(",\"distancia\":");

    if (duracion == 0 || distancia < 2 || distancia > 400) {
      Serial.print("null");
    } else {
      Serial.print(distancia, 1);
    }
    Serial.println("}");
  }
}
