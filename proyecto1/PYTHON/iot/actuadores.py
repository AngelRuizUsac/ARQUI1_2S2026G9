from configuracion import (TEMPERATURA_MAXIMA,LUZ_MINIMA,DISTANCIA_PUERTA)


# Estado actual de los dispositivos
estado_actuadores = {
    "ventilador": "APAGADO",
    "alarma": "APAGADA",
    "puerta": "CERRADA",
    "luces": "APAGADAS",
    "modo_luces": "AUTOMATICO"
}


# Permite recordar si la alarma fue silenciada
alarma_silenciada = False


def controlar_actuadores(datos, estado):

    global alarma_silenciada

    temperatura = datos["temperatura"]
    distancia = datos["distancia"]
    luz = datos["luz"]

    # ventilador

    if temperatura > TEMPERATURA_MAXIMA:
        estado_actuadores["ventilador"] = "ENCENDIDO"
    else:
        estado_actuadores["ventilador"] = "APAGADO"

    # Emergencia

    if estado == "EMERGENCIA":

        estado_actuadores["puerta"] = "ABIERTA"

        if not alarma_silenciada:
            estado_actuadores["alarma"] = "ENCENDIDA"

    else:
        estado_actuadores["alarma"] = "APAGADA"

        # Si ya no hay emergencia permitimos nuevamente la alarma
        alarma_silenciada = False

        # Apertura automática por distancia.
        if distancia < DISTANCIA_PUERTA:
            estado_actuadores["puerta"] = "ABIERTA"
        else:
            estado_actuadores["puerta"] = "CERRADA"

    # Iluminación

    if estado_actuadores["modo_luces"] == "AUTOMATICO":

        if luz < LUZ_MINIMA:
            estado_actuadores["luces"] = "ENCENDIDAS"
        else:
            estado_actuadores["luces"] = "APAGADAS"

    return estado_actuadores.copy()


def ejecutar_comando(comando):
    # Ejecuta comandos desde MQTT

    global alarma_silenciada

    tipo = comando.get("comando",comando.get("command", ""))

    accion = comando.get("accion",comando.get("action", ""))

    tipo = tipo.lower()
    accion = accion.lower()

    # Puerta

    if tipo == "puerta":

        if accion == "abrir":
            estado_actuadores["puerta"] = "ABIERTA"

        elif accion == "cerrar":
            estado_actuadores["puerta"] = "CERRADA"

    # Luces

    elif tipo == "luces":

        if accion == "encender":
            estado_actuadores["modo_luces"] = "MANUAL"
            estado_actuadores["luces"] = "ENCENDIDAS"

        elif accion == "apagar":
            estado_actuadores["modo_luces"] = "MANUAL"
            estado_actuadores["luces"] = "APAGADAS"

        elif accion == "automatico":
            estado_actuadores["modo_luces"] = "AUTOMATICO"

    # Alarma

    elif tipo == "alarma":

        if accion == "silenciar":
            alarma_silenciada = True
            estado_actuadores["alarma"] = "APAGADA"

    return estado_actuadores.copy()