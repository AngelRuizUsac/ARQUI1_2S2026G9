
from configuracion import TEMPERATURA_MAXIMA, HUMEDAD_MINIMA, HUMEDAD_MAXIMA, GAS_MAXIMO


def obtener_estado(datos):
    gas = datos.get("gas")
    if type(gas) is int and 0 <= gas <= 1023 and gas > GAS_MAXIMO:
        return "EMERGENCIA"
    temperatura = datos.get("temperatura")
    humedad = datos.get("humedad")
    if (temperatura is not None and temperatura > TEMPERATURA_MAXIMA
            or humedad is not None and not HUMEDAD_MINIMA <= humedad <= HUMEDAD_MAXIMA):
        return "ADVERTENCIA"


    return "NORMAL"
