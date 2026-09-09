import time

from sensores import leer_sensores
from estado import actualizar_estado
from actuadores import controlar_actuadores, ejecutar_comando

from Globals import shared

from configuracion import INTERVALO_LECTURA

from base_datos import BaseDatos
from mqtt_cliente import ClienteMQTT

from arm64 import agregar_temperatura



def mostrar_informacion(actuadores):
    

    print("\n===================================")
    print("       EDIFICIO INTELIGENTE")
    print("===================================")

    print("\nSENSORES")

    print(f"Temperatura: {shared.temperatura} °C")
    print(f"Humedad: {shared.humedad} %")
    print(f"Gas: {shared.gas}")
    print(f"Distancia: {shared.distancia} cm")
    print(f"Luz: {shared.luz}")

    print(f"\nEstado general: {shared.estado_global}")

    print("\nACTUADORES")

    print(f"Ventilador: {actuadores['ventilador']}")
    print(f"Alarma: {actuadores['alarma']}")
    print(f"Puerta: {actuadores['puerta']}")
    print(f"Luces: {actuadores['luces']}")
    print(f"Modo luces: {actuadores['modo_luces']}")

    print("===================================")



def main():

    print("Iniciando sistema del edificio inteligente...")

    # Inicializa conexión con MongoDB

    base_datos = BaseDatos()

    # Inicializa conexión MQTT
    mqtt = ClienteMQTT()
    mqtt.conectar()

    estado_anterior = None

    try:

        while True:

            # Lee los valores actuales de sensores

            leer_sensores()
            # Actualiza el estado general del edificio
            estado = actualizar_estado()

            # Controla los actuadores automáticamente
            actuadores = controlar_actuadores()

            # Muestra información actual del sistema
            mostrar_informacion(actuadores)

            # Guarda lecturas en MongoDB
            base_datos.guardar_lectura(
                {
                    "temperatura": shared.temperatura,
                    "humedad": shared.humedad,
                    "gas": shared.gas,
                    "distancia": shared.distancia,
                    "luz": shared.luz
                })


            # Guarda el estado actual del edificio

            base_datos.guardar_estado(estado)


            # Registra cambios de estado

            if estado != estado_anterior:
                base_datos.guardar_evento("CAMBIO_ESTADO",f"Estado cambiado a {estado}")
                estado_anterior = estado

            # Publica datos mediante MQTT

            mqtt.publicar_lecturas(
                {
                    "temperatura": shared.temperatura,
                    "humedad": shared.humedad,
                    "gas": shared.gas,
                    "distancia": shared.distancia,
                    "luz": shared.luz
                }
            )

            mqtt.publicar_estado(estado)
            mqtt.publicar_actuadores(actuadores)

            # Revisa comandos enviados desde dashboard

            comando = mqtt.obtener_comando()
            while comando is not None:

                print(f"\nEjecutando comando: {comando}")

                ejecutar_comando(comando)

                base_datos.guardar_comando(comando)

                comando = mqtt.obtener_comando()



            # Envía temperaturas acumuladas a ARM64

            resultado_arm64 = agregar_temperatura(shared.temperatura)

            if resultado_arm64:

                print("\nResultado ARM64:")
                print(resultado_arm64)


                base_datos.guardar_resultado_arm64(resultado_arm64)

                mqtt.publicar_resultado_arm64(resultado_arm64)



            # Espera antes de la siguiente lectura

            time.sleep(INTERVALO_LECTURA)


    except KeyboardInterrupt:

        print("\nSistema detenido por el usuario.")


    finally:

        mqtt.cerrar()
        base_datos.cerrar()



if __name__ == "__main__":

    main()