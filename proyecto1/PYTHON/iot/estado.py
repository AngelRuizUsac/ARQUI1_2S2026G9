from configuracion import (
    TEMPERATURA_MAXIMA,
    HUMEDAD_MINIMA,
    HUMEDAD_MAXIMA,
    GAS_MAXIMO)

from Globals import shared

def actualizar_estado():
   
    temperatura = shared.temperatura
    humedad = shared.humedad
    gas = shared.gas



    # El gas tiene prioridad porque representa una situación peligrosa

    if gas > GAS_MAXIMO:
        shared.estado_global = "EMERGENCIA"
        return shared.estado_global


    # Temperatura o humedad fuera del rango permitido

    if temperatura > TEMPERATURA_MAXIMA:
        shared.estado_global = "ADVERTENCIA"
        return shared.estado_global


    if humedad < HUMEDAD_MINIMA:
        shared.estado_global = "ADVERTENCIA"
        return shared.estado_global


    if humedad > HUMEDAD_MAXIMA:
        shared.estado_global = "ADVERTENCIA"
        return shared.estado_global
    shared.estado_global = "NORMAL"


    return shared.estado_global