
import time
from configuracion import LCD_DIRECCION, LCD_BUS


def escribir(lcd, linea1, linea2):

    lcd.text(str(linea1)[:16].ljust(16), 1)
    lcd.text(str(linea2)[:16].ljust(16), 2)


def crear_paginas(datos, estado, actuadores=None):

    def valor(clave, unidad):
        dato = datos.get(clave)
        return "SIN DATOS" if dato is None else f"{dato:.1f}{unidad}"

    paginas = [
        ("T:" + valor("temperatura", " C"), "H:" + valor("humedad", "%")),
        ("Gas:" + valor("gas", ""), "Luz:" + valor("luz", "%")),
        ("Distancia", valor("distancia", " cm")),
        ("Estado global", estado),
        ("Puerta", (actuadores or {}).get("puerta", "SIN DATOS")),
    ]
    if datos.get("dht11_reutilizado"):
        paginas[0] = tuple(linea + " *" for linea in paginas[0])
    for sensor, detalle in datos.get("errores", {}).items():
        if sensor == "DHT11" and datos.get("dht11_reutilizado"):
            paginas.append(("DHT11 anterior", "Hace %.0f s" % datos["dht11_antiguedad_s"]))
            continue
        titulo = "Fallo USB/Uno" if sensor == "Arduino USB" else f"Fallo {sensor}"
        paginas.append((titulo, "Desconectada" if sensor == "LDR" and "configuracion" in detalle else "Reintentando..."))
    return paginas


class Pantalla:

    def __init__(self):
        from rpi_lcd import LCD
        self.lcd = LCD(LCD_DIRECCION, LCD_BUS, 16, 2, True)
        self.pagina = 0
        self.estado_anterior = None
        escribir(self.lcd, "Iniciando...", "Esperando datos")

    def actualizar(self, datos, estado, actuadores=None):
        paginas = crear_paginas(datos, estado, actuadores)
        self.pagina %= len(paginas)
        if estado == "EMERGENCIA" and self.estado_anterior != estado:
            self.pagina = 3
        escribir(self.lcd, *paginas[self.pagina])
        self.estado_anterior = estado
        self.pagina = (self.pagina + 1) % len(paginas)

    def mostrar_error(self, error):
        origen = getattr(error, "sensor", "Lectura")
        titulo = "Fallo USB/Uno" if origen == "Arduino USB" else f"Fallo {origen}"
        escribir(self.lcd, titulo, "Reintentando...")

    def cerrar(self):
        self.lcd.clear()


def mostrar_sistema():
    from rpi_lcd import LCD
    from configuracion import INTERVALO_LECTURA
    from sensores import leer_sensores_disponibles, cerrar_sensores
    from estado import obtener_estado

    lcd = None
    pagina = 0
    fallos = 0
    estado_anterior = None
    try:
        lcd = LCD(LCD_DIRECCION, LCD_BUS, 16, 2, True)
        escribir(lcd, "Iniciando...", "Sensores reales")
        print("LCD con sensores reales. Ctrl+C para terminar.")
        while True:
            try:
                datos = leer_sensores_disponibles()
            except RuntimeError as error:
                fallos += 1

                origen = getattr(error, "sensor", "Lectura")
                if origen == "Arduino USB":
                    origen = "USB Arduino"
                escribir(lcd, f"Fallo {origen}" if origen != "USB Arduino" else "Fallo USB/Uno",
                         "Reintentando...")
                print(f"Lectura descartada ({fallos}): {error}")
            else:
                fallos = 0
                estado = obtener_estado(datos)
                paginas = crear_paginas(datos, estado)
                pagina %= len(paginas)

                if estado == "EMERGENCIA" and estado_anterior != estado:
                    pagina = 3
                linea1, linea2 = paginas[pagina]
                escribir(lcd, linea1, linea2)
                print(f"{linea1} | {linea2}")
                estado_anterior = estado
                pagina = (pagina + 1) % len(paginas)
            time.sleep(max(3, INTERVALO_LECTURA))
    except KeyboardInterrupt:
        print("\nPantalla detenida.")
    finally:
        try:
            if lcd is not None:
                lcd.clear()
        finally:
            cerrar_sensores()


def probar_lcd():
    from rpi_lcd import LCD

    lcd = LCD(LCD_DIRECCION, LCD_BUS, 16, 2, True)
    try:
        lcd.text("Hola Mundo!", 1)
        lcd.text("LCD I2C", 2)
        time.sleep(10)
    finally:
        lcd.clear()


if __name__ == "__main__":
    mostrar_sistema()
