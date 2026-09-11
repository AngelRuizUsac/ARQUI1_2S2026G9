
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from configuracion import INTERVALO_LECTURA
from sensores import leer_sensores_disponibles, cerrar_sensores
from actuadores import Controlador
from hardware import Hardware
from base_datos import BaseDatos
from mqtt_cliente import ClienteMQTT
from arm64 import agregar_temperatura


def mostrar_informacion(
    datos,
    estado,
    actuadores
):
    """
    Muestra en consola el estado actual
    del edificio.
    """

    print("\n===================================")
    print("       EDIFICIO INTELIGENTE")
    print("===================================")

    print("\nSENSORES")

    print(
        f"Temperatura: "
        f"{datos.get('temperatura') if datos.get('temperatura') is not None else 'SIN DATOS'} °C"
    )

    print(
        f"Humedad: "
        f"{datos.get('humedad') if datos.get('humedad') is not None else 'SIN DATOS'} %"
    )

    print(
        f"Gas: "
        f"{datos.get('gas') if datos.get('gas') is not None else 'SIN DATOS'}"
    )

    print(
        f"Distancia: "
        f"{datos.get('distancia') if datos.get('distancia') is not None else 'SIN DATOS'} cm"
    )

    print(
        f"Luz: "
        f"{datos.get('luz') if datos.get('luz') is not None else 'SIN DATOS'}"
    )

    print(
        f"\nEstado general: {estado}"
    )

    print("\nACTUADORES")

    print(
        f"Ventilador: "
        f"{actuadores['ventilador']}"
    )

    print(
        f"Alarma: "
        f"{actuadores['alarma']}"
    )

    print(
        f"Puerta: "
        f"{actuadores['puerta']}"
    )

    print(
        f"Luces: "
        f"{actuadores['luces']}"
    )

    print(
        f"Modo luces: "
        f"{actuadores['modo_luces']}"
    )

    if datos.get("errores"):
        print("\nAVISOS DE SENSORES")
        for sensor, detalle in datos["errores"].items():
            print(f"{sensor}: {detalle}")

    print("===================================")


def main():
    print("HARDWARE REAL: Raspberry Pi 4 + Arduino USB")
    db, mqtt = BaseDatos(), ClienteMQTT()
    controlador = Controlador()
    hardware = pantalla = None
    tareas = ThreadPoolExecutor(max_workers=3)
    lectura = calculo = historial = None
    siguiente = 0
    anterior = None
    vistos = OrderedDict()
    try:
        hardware = Hardware()
        from pantalla import Pantalla
        pantalla = Pantalla()
        mqtt.conectar()
        while True:
            ahora = time.monotonic()
            nueva = False
            if lectura is None and ahora >= siguiente:
                lectura = tareas.submit(leer_sensores_disponibles)
            if lectura is not None and lectura.done():
                try:
                    datos = lectura.result()
                except Exception as error:
                    datos = dict.fromkeys(("temperatura", "humedad", "gas", "luz", "distancia"))
                    datos["errores"] = {"lectura": str(error)}
                datos.update(timestamp=datetime.now(timezone.utc).isoformat())
                controlador.actualizar(datos)
                db.guardar_lectura(datos)
                mqtt.publicar_lecturas(datos)
                nueva = True
                lectura = None
                siguiente = ahora + INTERVALO_LECTURA
                if datos.get("temperatura") is not None and not datos.get("dht11_reutilizado"):
                    if calculo is None:
                        calculo = tareas.submit(agregar_temperatura, datos["temperatura"])
                    else:
                        db.guardar_evento("ARM64_OCUPADO", "Lectura omitida: calculo anterior sigue activo")
            controlador.actualizar()

            for origen, obtener in (("panel", hardware.obtener_comando), ("dashboard", mqtt.obtener_comando)):
                for _ in range(20):
                    comando = obtener()
                    if comando is None:
                        break
                    identificador = comando.get("id")
                    if not isinstance(identificador, str) or len(identificador) > 100:
                        identificador = None
                    if identificador and identificador in vistos:
                        mqtt.publicar("control/respuesta", vistos[identificador])
                        continue
                    vencido = False
                    if origen == "dashboard" and "ts" in comando:
                        try:
                            edad = (datetime.now(timezone.utc) - datetime.fromisoformat(comando["ts"].replace("Z", "+00:00"))).total_seconds()
                            vencido = edad > 15 or edad < -30
                        except (ValueError, TypeError, AttributeError):
                            vencido = True
                    resultado = dict(aceptado=False, mensaje="Comando vencido o fecha invalida") if vencido else controlador.ejecutar(comando)
                    hardware.aplicar(controlador.salidas, controlador.estado)
                    resultado.update(id=identificador, origen=origen)
                    db.guardar_comando({**comando, **resultado})
                    mqtt.publicar("control/respuesta", resultado)
                    if identificador:
                        vistos[identificador] = resultado
                        if len(vistos) > 500:
                            vistos.popitem(last=False)
            hardware.aplicar(controlador.salidas, controlador.estado)
            actual = (controlador.estado, controlador.salidas.copy())
            if actual != anterior:
                if anterior is None or anterior[0] != actual[0]:
                    db.guardar_evento("CAMBIO_ESTADO", f"{anterior[0] if anterior else 'INICIO'} -> {actual[0]}")
                    db.guardar_estado(actual[0])
                for nombre, valor in actual[1].items():
                    if anterior is None or anterior[1].get(nombre) != valor:
                        db.guardar_evento("CAMBIO_ACTUADOR", f"{nombre}: {valor}")
            if nueva or actual != anterior:
                mostrar_informacion(controlador.datos, controlador.estado, controlador.salidas)
                mqtt.publicar_estado(controlador.estado)
                mqtt.publicar_actuadores(controlador.salidas)
                mqtt.publicar("diagnostico", {"errores": controlador.datos.get("errores", {})})
                if pantalla:
                    pantalla.actualizar(controlador.datos, controlador.estado, controlador.salidas)
            anterior = actual
            if calculo is not None and calculo.done():
                resultado = calculo.result()
                calculo = None
                if resultado:
                    print("\nResultado ARM64:", resultado)
                    resultado.update(timestamp=datetime.now(timezone.utc).isoformat())
                    db.guardar_resultado_arm64(resultado)
                    mqtt.publicar_resultado_arm64(resultado)
            if historial is None or historial.done():
                if historial is not None:
                    historial.result()
                historial = tareas.submit(mqtt.responder_historial, db)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Sistema detenido")
    finally:

        tareas.shutdown(wait=True, cancel_futures=True)
        if hardware:
            hardware.cerrar()
        if pantalla:
            pantalla.cerrar()
        cerrar_sensores()
        mqtt.cerrar()
        db.cerrar()


if __name__ == "__main__":
    main()
