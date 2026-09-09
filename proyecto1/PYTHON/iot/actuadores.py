from configuracion import (
    TEMPERATURA_MAXIMA,
    LUZ_MINIMA,
    DISTANCIA_PUERTA)

from Globals import shared

def controlar_actuadores():

    # Control del ventilador

    if shared.temperatura > TEMPERATURA_MAXIMA:
        shared.ventilador = True
    else:
        shared.ventilador = False


    # Control de alarma y puerta por emergencia

    if shared.estado_global == "EMERGENCIA":
        shared.alarma = True
        shared.puerta = True


    else:

        shared.alarma = False


        if shared.distancia < DISTANCIA_PUERTA:
            shared.puerta = True
        else:
            shared.puerta = False



    # Control automático de iluminación

    if shared.luz < LUZ_MINIMA:
        shared.luces = True
    else:
        shared.luces = False

    return obtener_estado_actuadores()




def obtener_estado_actuadores():

    return {

        "ventilador": shared.ventilador,
        "alarma": shared.alarma,
        "puerta": shared.puerta,
        "luces": shared.luces,
        "modo_luces": shared.modo_luces}




def ejecutar_comando(comando):

    tipo = comando.get("comando","")

    accion = comando.get("accion","")
    tipo = tipo.lower()
    accion = accion.lower()


    if tipo == "puerta":
        if accion == "abrir":
            shared.puerta = True
        elif accion == "cerrar":
            shared.puerta = False


    elif tipo == "luces":

        if accion == "encender":
            shared.luces = True
            shared.modo_luces = "MANUAL"


        elif accion == "apagar":
            shared.luces = False
            shared.modo_luces = "MANUAL"

        elif accion == "automatico":
            shared.modo_luces = "AUTOMATICO"


    elif tipo == "alarma":
        if accion == "silenciar":
            shared.alarma = False

    return obtener_estado_actuadores()