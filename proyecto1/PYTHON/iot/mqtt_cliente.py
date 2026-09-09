import json

import paho.mqtt.client as mqtt

from configuracion import (
    MQTT_ACTIVO,
    MQTT_BROKER,
    MQTT_PUERTO,
    MQTT_USUARIO,
    MQTT_PASSWORD,
    IDENTIFICADOR_UNICO)



class ClienteMQTT:

    def __init__(self):

        self.activo = MQTT_ACTIVO

        self.cliente = None

        self.comandos = []


        if not self.activo:

            print("MQTT desactivado.")
            return


        self.cliente = mqtt.Client(client_id=IDENTIFICADOR_UNICO)


        if MQTT_USUARIO:
            self.cliente.username_pw_set(MQTT_USUARIO,MQTT_PASSWORD)



        self.cliente.on_connect = self.al_conectar

        self.cliente.on_message = self.al_recibir



    def conectar(self):

        if not self.activo:
            return

        try:

            self.cliente.connect(MQTT_BROKER,MQTT_PUERTO)

            self.cliente.loop_start()

            print("MQTT conectado.")



        except Exception as error:


            print(f"Error conectando MQTT: {error}")


    def al_conectar(self,cliente,datos,flags,codigo):


        if codigo == 0:

            print("Broker MQTT disponible.")

            cliente.subscribe("edificio/control/remoto")


    def al_recibir(self,cliente,datos,mensaje):


        try:

            comando = json.loads(mensaje.payload.decode())

            self.comandos.append(comando)

        except Exception as error:

            print(f"Error procesando MQTT: {error}")


    def publicar(self,ruta,datos):


        if not self.activo:
            return


        mensaje = json.dumps(datos)

        self.cliente.publish(ruta,mensaje)


    def publicar_lecturas(self,datos):


        self.publicar("edificio/sensores",datos)

    def publicar_estado(self,estado):

        self.publicar("edificio/estado/global",{"estado": estado})


    def publicar_actuadores(self,actuadores):

        self.publicar("edificio/actuadores",actuadores)


    def publicar_resultado_arm64(self,resultado):


        self.publicar("edificio/arm64/resultados",resultado)



    def obtener_comando(self):

        if len(self.comandos) > 0:
            return self.comandos.pop(0)
        return None




    def cerrar(self):

        if self.cliente:

            self.cliente.loop_stop()
            self.cliente.disconnect()