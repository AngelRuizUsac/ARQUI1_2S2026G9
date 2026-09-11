import os
from pathlib import Path
from dotenv import load_dotenv


# Carga las variables guardadas en el archivo .env
load_dotenv(Path(__file__).with_name('.env'))


def obtener_booleano(nombre, valor_por_defecto="false"):

    # Convierte una variable del archivo .env en True o False

    valor = os.getenv(nombre, valor_por_defecto)
    return valor.lower() == "true"


# Configuración general del sistema


INTERVALO_LECTURA = int(os.getenv("INTERVALO_LECTURA", "5"))


DHT_GPIO = int(os.getenv("DHT_GPIO", "4"))


ARDUINO_PUERTO = os.getenv("ARDUINO_PUERTO", "/dev/ttyACM0")
ARDUINO_BAUDIOS = 9600
LDR_ACTIVA = obtener_booleano("LDR_ACTIVA", "true")


## Configuración de los sensores y actuadores

TEMPERATURA_MAXIMA = float(os.getenv("TEMPERATURA_MAXIMA", "30"))

HUMEDAD_MINIMA = float(os.getenv("HUMEDAD_MINIMA", "40"))

HUMEDAD_MAXIMA = float(os.getenv("HUMEDAD_MAXIMA", "70"))

GAS_MAXIMO = int(os.getenv("GAS_MAXIMO", "100"))

LUZ_MINIMA = int(os.getenv("LUZ_MINIMA", "40"))

DISTANCIA_PUERTA = float(os.getenv("DISTANCIA_PUERTA", "15"))


# MQTT Confi !!!!!!!

MQTT_ACTIVO = obtener_booleano("MQTT_ACTIVO", "false")

MQTT_BROKER = os.getenv("MQTT_BROKER","localhost")

MQTT_PUERTO = int(os.getenv("MQTT_PUERTO", "1883"))

MQTT_USUARIO = os.getenv("MQTT_USUARIO","")

MQTT_PASSWORD = os.getenv("MQTT_PASSWORD","")

MQTT_TLS = obtener_booleano("MQTT_TLS","false")

IDENTIFICADOR_UNICO = os.getenv("IDENTIFICADOR_UNICO","ARQUI1")


# MONGO Confi

MONGO_ACTIVO = obtener_booleano("MONGO_ACTIVO","false")

MONGO_URI = os.getenv("MONGO_URI","")

MONGO_BASE_DATOS = os.getenv("MONGO_BASE_DATOS","edificio_inteligente")


# arm64 Confi

# Cantidad de temperaturas que se enviarán al módulo ARM64.
LECTURAS_ARM64 = int(os.getenv("LECTURAS_ARM64", "20"))

# proyecto1/
RUTA_PROYECTO = Path(__file__).resolve().parents[2]

# proyecto1/ARM64/
RUTA_ARM64 = RUTA_PROYECTO / "ARM64"

BINARIO_ARM64 = os.getenv("BINARIO_ARM64","programa")


PUERTA_SEGUNDOS = float(os.getenv("PUERTA_SEGUNDOS", "5"))
DHT_MAX_EDAD = float(os.getenv("DHT_MAX_EDAD", "15"))
GPIO_LUCES = tuple(int(p) for p in os.getenv("GPIO_LUCES", "17,23,24,25").split(","))
GPIO_SERVO = int(os.getenv("GPIO_SERVO", "18"))
GPIO_VENTILADOR = int(os.getenv("GPIO_VENTILADOR", "12"))
GPIO_BUZZER = int(os.getenv("GPIO_BUZZER", "16"))
GPIO_VERDE = int(os.getenv("GPIO_VERDE", "5"))
GPIO_AMARILLO = int(os.getenv("GPIO_AMARILLO", "6"))
GPIO_ROJO = int(os.getenv("GPIO_ROJO", "13"))
GPIO_LED_PUERTA = int(os.getenv("GPIO_LED_PUERTA", "19"))
GPIO_LED_VENTILADOR = int(os.getenv("GPIO_LED_VENTILADOR", "26"))
GPIO_BOTONES = tuple(int(p) for p in os.getenv("GPIO_BOTONES", "20,21,22,27").split(","))
SERVO_CERRADO = float(os.getenv("SERVO_CERRADO", "-1"))
SERVO_ABIERTO = float(os.getenv("SERVO_ABIERTO", "1"))
SERVO_PULSO_MIN = float(os.getenv("SERVO_PULSO_MIN", "0.001"))
SERVO_PULSO_MAX = float(os.getenv("SERVO_PULSO_MAX", "0.002"))
VENTILADOR_ACTIVO_ALTO = obtener_booleano("VENTILADOR_ACTIVO_ALTO", "true")
LCD_DIRECCION = int(os.getenv("LCD_DIRECCION", "0x27"), 0)
LCD_BUS = int(os.getenv("LCD_BUS", "1"))
if INTERVALO_LECTURA < 2 or PUERTA_SEGUNDOS <= 0 or DHT_MAX_EDAD < 0:
    raise ValueError("Intervalo >= 2 s, puerta > 0 s y edad DHT >= 0 requeridos")
if not 20 <= LECTURAS_ARM64 <= 200:
    raise ValueError("LECTURAS_ARM64 debe estar entre 20 y 200")


BUZZER_FRECUENCIA = int(os.getenv("BUZZER_FRECUENCIA", "2000"))
if BUZZER_FRECUENCIA <= 0:
    raise ValueError("BUZZER_FRECUENCIA debe ser positiva")
