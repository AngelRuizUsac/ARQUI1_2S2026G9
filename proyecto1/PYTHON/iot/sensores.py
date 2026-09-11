import time
import json
import math
from threading import RLock

from configuracion import DHT_GPIO, INTERVALO_LECTURA
from configuracion import ARDUINO_PUERTO, ARDUINO_BAUDIOS
from configuracion import LDR_ACTIVA, DHT_MAX_EDAD


_dht = None
_arduino = None
_usb_lock = RLock()
_ventilador_envio = None
_ventilador_tiempo = 0
_ultimo_ambiente = None
_ultimos_valores = {}
_ultimo_ambiente_tiempo = None


class ErrorSensor(RuntimeError):

    def __init__(self, sensor, detalle):
        self.sensor = sensor
        super().__init__(f"{sensor}: {detalle}")


def interpretar_arduino(linea, parcial=False):

    try:
        datos = json.loads(linea)
        if not isinstance(datos, dict):
            raise ValueError("Se esperaba un objeto JSON")
    except (ValueError, TypeError, KeyError) as error:
        raise ErrorSensor("Arduino USB", "Mensaje inválido del Arduino") from error
    resultado = {}
    errores = {}
    for clave, nombre in (("gas", "MQ-2"), ("luz_adc", "LDR"), ("distancia", "HC-SR04")):
        valor = datos.get(clave)
        valido = (type(valor) is int and 0 <= valor <= 1023) if clave != "distancia" else (
            type(valor) in (int, float) and math.isfinite(valor) and 2 <= valor <= 400)
        if not valido:
            detalle = "Sin eco valido" if clave == "distancia" and valor is None else f"Campo {clave} ausente o invalido"
            if not parcial and not (clave == "distancia" and valor is None and clave in datos):
                raise ErrorSensor(nombre, detalle)
            errores[nombre] = detalle
            valor = None
        resultado[clave] = valor
    resultado["luz"] = (round(resultado["luz_adc"] * 100 / 1023, 1)
                        if resultado["luz_adc"] is not None else None)
    if parcial:
        resultado["errores"] = errores
    return resultado



def leer_arduino(parcial=False):
    with _usb_lock:
        return _leer_arduino(parcial)


def enviar_ventilador(encendido, forzar=False):




    global _ventilador_envio, _ventilador_tiempo
    if not _usb_lock.acquire(blocking=forzar):
        return False
    try:
        if _arduino is None:
            return False
        ahora = time.monotonic()
        if not forzar and encendido == _ventilador_envio and ahora - _ventilador_tiempo < 1:
            return True
        try:
            _arduino.write(b"F" if encendido else b"f")
        except (OSError, RuntimeError) as error:
            print(f"Ventilador USB: no se pudo enviar ({type(error).__name__})")
            return False
        _ventilador_envio, _ventilador_tiempo = encendido, ahora
        return True
    finally:
        _usb_lock.release()


def _leer_arduino(parcial=False):
    global _arduino, _ventilador_envio
    try:
        import serial
    except ImportError as error:
        raise ErrorSensor("Arduino USB", "Falta pyserial: instala requirements.txt") from error
    try:
        if _arduino is None:
            _arduino = serial.Serial(ARDUINO_PUERTO, ARDUINO_BAUDIOS, timeout=3, write_timeout=0.2)
            _ventilador_envio = None
            time.sleep(2)

        _arduino.reset_input_buffer()
        _arduino.write(b"L")
        linea = _arduino.readline(128)
        if not linea.endswith(b"\n"):
            raise ErrorSensor("Arduino USB", "Sin respuesta completa; revisa el programa y el USB")
        return interpretar_arduino(linea.decode("ascii"), parcial=parcial)
    except serial.SerialException as error:
        if _arduino is not None:
            try:
                _arduino.close()
            finally:
                _arduino = None
        raise ErrorSensor("Arduino USB", f"No se pudo usar {ARDUINO_PUERTO}: {error}") from error
    except UnicodeDecodeError as error:
        raise ErrorSensor("Arduino USB", "Respuesta ilegible del Arduino") from error


def leer_dht11():

    global _dht
    if _dht is None:
        try:
            import board
            import adafruit_dht
        except ImportError as error:
            raise ErrorSensor("DHT11",
                "Falta instalar adafruit-circuitpython-dht en la Raspberry."
            ) from error
        try:
            pin = getattr(board, f"D{DHT_GPIO}")
            _dht = adafruit_dht.DHT11(pin, use_pulseio=False)
        except (RuntimeError, OSError, ValueError, AttributeError) as error:
            raise ErrorSensor("DHT11", f"No se pudo inicializar GPIO{DHT_GPIO}: {error}") from error

    try:
        temperatura = _dht.temperature
        humedad = _dht.humidity
    except (RuntimeError, OSError) as error:
        raise ErrorSensor("DHT11", str(error)) from error
    if temperatura is None or humedad is None:
        raise ErrorSensor("DHT11", "Lectura incompleta")
    return {"temperatura": temperatura, "humedad": humedad}


def cerrar_sensores():
    global _dht, _arduino, _ultimo_ambiente, _ultimo_ambiente_tiempo
    _ultimos_valores.clear()
    _ultimo_ambiente = None
    _ultimo_ambiente_tiempo = None
    if _arduino is not None:
        try:
            _arduino.close()
        finally:
            _arduino = None
    if _dht is not None:
        try:
            _dht.exit()
        finally:
            _dht = None


def leer_sensores():

    return leer_sensores_reales()


def leer_sensores_disponibles():

    global _ultimo_ambiente, _ultimo_ambiente_tiempo
    datos = dict.fromkeys(("temperatura", "humedad", "gas", "luz", "distancia"))
    errores = {}
    try:
        ambiente = leer_dht11()
        _ultimo_ambiente = ambiente.copy()
        _ultimo_ambiente_tiempo = time.monotonic()
        datos.update(ambiente)
        datos["dht11_reutilizado"] = False
        datos["dht11_antiguedad_s"] = 0
    except RuntimeError as error:
        errores["DHT11"] = str(error)
        datos["dht11_reutilizado"] = _ultimo_ambiente is not None
        datos["dht11_antiguedad_s"] = None
        if _ultimo_ambiente is not None:
            datos.update(_ultimo_ambiente)
            edad = round(time.monotonic() - _ultimo_ambiente_tiempo, 1)
            datos["dht11_antiguedad_s"] = edad
            errores["DHT11"] += f"; usando ultima lectura valida de hace {edad} s"
    try:
        arduino = leer_arduino(parcial=True)
        errores.update(arduino.get("errores", {}))
        datos["gas"] = arduino["gas"]
        datos["distancia"] = arduino["distancia"]
        datos["luz"] = arduino["luz"] if LDR_ACTIVA else None
        if arduino["distancia"] is None:
            errores["HC-SR04"] = "Sin eco valido"
    except RuntimeError as error:
        errores[getattr(error, "sensor", "Arduino USB")] = str(error)
    if not LDR_ACTIVA:
        errores["LDR"] = "Desconectada por configuracion"
    reutilizados = {}
    antiguedades = {}
    ahora = time.monotonic()
    for clave in ("temperatura", "humedad", "gas", "luz", "distancia"):
        previo_dht = clave in ("temperatura", "humedad") and datos.get("dht11_reutilizado", False)
        if datos.get(clave) is not None and not previo_dht:
            _ultimos_valores[clave] = (datos[clave], ahora)
            reutilizados[clave] = False
            antiguedades[clave] = 0
        elif clave in _ultimos_valores and not (clave == "luz" and not LDR_ACTIVA):
            datos[clave], instante = _ultimos_valores[clave]
            reutilizados[clave] = True
            antiguedades[clave] = round(ahora - instante, 1)
            errores.setdefault(clave, f"Usando lectura anterior de hace {antiguedades[clave]} s")
        else:
            reutilizados[clave] = False
            antiguedades[clave] = None
    datos["reutilizados"] = reutilizados
    datos["antiguedades_s"] = antiguedades
    datos["errores"] = errores
    return datos


def leer_sensores_reales():
    ambiente = leer_dht11()
    arduino = leer_arduino()
    if arduino["distancia"] is None:
        raise ErrorSensor("HC-SR04", "Sin eco válido: coloca un objeto entre 2 y 400 cm")
    return {**ambiente, "gas": arduino["gas"],
            "luz": arduino["luz"], "distancia": arduino["distancia"]}


def mostrar_sensores(sensor="todos"):

    print("Lecturas reales. Ctrl+C para terminar.")

    anteriores = {}
    campos = [("temperatura", "Temperatura", "°C"), ("humedad", "Humedad", "%"),
              ("gas", "Gas ADC", ""), ("luz", "Luz", "%"), ("distancia", "Distancia", "cm")]
    if sensor == "dht11":
        campos = campos[:2]
    elif sensor == "arduino":
        campos = campos[2:]
    try:
        while True:
            try:
                if sensor == "todos":
                    datos = leer_sensores_disponibles()
                elif sensor == "dht11":
                    datos = leer_dht11()
                else:
                    datos = leer_arduino(parcial=True)
            except RuntimeError as error:
                datos = {"errores": {getattr(error, "sensor", "Sensor"): str(error)}}
            ahora = time.monotonic()
            partes = []
            for clave, etiqueta, unidad in campos:
                valor = datos.get(clave)
                reutilizado = datos.get("reutilizados", {}).get(clave, False) or (clave in ("temperatura", "humedad") and datos.get("dht11_reutilizado", False))
                if valor is not None and not reutilizado:
                    anteriores[clave] = (valor, ahora)
                    texto = f"{valor} {unidad}".strip()
                elif clave in anteriores:
                    anterior, instante = anteriores[clave]
                    texto = f"{anterior} {unidad} [anterior, {ahora - instante:.1f} s]"
                else:
                    texto = "SIN DATOS (aun no hay lectura valida)"
                partes.append(f"{etiqueta}: {texto}")
            print(" | ".join(partes))
            for origen, detalle in datos.get("errores", {}).items():
                print(f"  Aviso {origen}: {detalle}")
            time.sleep(max(3, INTERVALO_LECTURA))
    except KeyboardInterrupt:
        print("\nPrueba terminada.")
    finally:
        cerrar_sensores()


if __name__ == "__main__":
    mostrar_sensores()
