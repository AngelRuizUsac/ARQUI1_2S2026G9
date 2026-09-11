
import json
import re
from queue import Queue, Empty, Full
import configuracion as cfg


class ClienteMQTT:
    def __init__(self):
        self.activo = cfg.MQTT_ACTIVO
        self.cliente = None
        self.comandos = Queue(maxsize=100)
        self.consultas = Queue(maxsize=20)

    def _topic(self, ruta):
        return f"{cfg.IDENTIFICADOR_UNICO}/edificio/{ruta}"

    def conectar(self):
        if not self.activo:
            print("MQTT desactivado")
            return
        import paho.mqtt.client as mqtt
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.cliente.on_connect = self._al_conectar
        self.cliente.on_message = self._al_recibir_mensaje
        if cfg.MQTT_USUARIO:
            self.cliente.username_pw_set(cfg.MQTT_USUARIO, cfg.MQTT_PASSWORD)
        if cfg.MQTT_TLS:
            self.cliente.tls_set()
        self.cliente.will_set(self._topic("conexion"), json.dumps({"conectado": False}), qos=1, retain=True)
        self.cliente.reconnect_delay_set(min_delay=1, max_delay=30)
        self.cliente.connect_async(cfg.MQTT_BROKER, cfg.MQTT_PUERTO, 30)
        self.cliente.loop_start()

    def _al_conectar(self, cliente, userdata, flags, reason_code, properties):
        if reason_code == 0:
            cliente.subscribe([(self._topic("control/remoto"), 1), (self._topic("historial/solicitud"), 0)])
            self.publicar("conexion", {"conectado": True}, retain=True)
        else:
            print(f"MQTT: conexion rechazada {reason_code}")

    def _al_recibir_mensaje(self, cliente, userdata, mensaje):

        if mensaje.retain or len(mensaje.payload) > 4096:
            return
        try:
            contenido = json.loads(mensaje.payload.decode("utf-8"))
            if not isinstance(contenido, dict):
                return
            cola = self.consultas if mensaje.topic == self._topic("historial/solicitud") else self.comandos
            cola.put_nowait(contenido)
        except (ValueError, UnicodeError, Full):
            print("MQTT: mensaje invalido o cola llena")

    def publicar(self, ruta, datos, retain=False):
        if self.cliente is not None and self.cliente.is_connected():
            self.cliente.publish(self._topic(ruta), json.dumps(datos, ensure_ascii=False), qos=1, retain=retain)

    def publicar_lecturas(self, datos):
        for clave in ("temperatura", "humedad", "gas", "distancia", "luz"):
            self.publicar(f"sensores/{clave}", {"valor": datos.get(clave), "timestamp": datos.get("timestamp"),
                          "reutilizado": datos.get("reutilizados", {}).get(clave, bool(datos.get("dht11_reutilizado")) if clave in ("temperatura", "humedad") else False)})

    def publicar_estado(self, estado):
        self.publicar("estado/global", {"estado": estado})

    def publicar_actuadores(self, actuadores):
        for clave in ("puerta", "luces", "ventilador", "alarma"):
            dato = {"estado": actuadores[clave]}
            if clave == "luces":
                dato.update(modo=actuadores["modo_luces"], zonas={f"zona{i+1}": actuadores["luces"] for i in range(len(cfg.GPIO_LUCES))})
            self.publicar(f"actuadores/{clave}", dato)

    def publicar_resultado_arm64(self, resultado):
        self.publicar("arm64/resultados", resultado)

    @staticmethod
    def _sacar(cola):
        try:
            return cola.get_nowait()
        except Empty:
            return None

    def obtener_comando(self):
        return self._sacar(self.comandos)

    def responder_historial(self, base_datos):
        consulta = self._sacar(self.consultas)
        if consulta is None:
            return
        identificador = consulta.get("id", "")
        if not isinstance(identificador, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", identificador):
            return
        respuesta = {"id": identificador, "coleccion": consulta.get("coleccion")}
        try:
            respuesta["documentos"] = base_datos.historial(consulta.get("coleccion"), consulta.get("limite", 40))
        except Exception as error:
            respuesta["error"] = str(error) if isinstance(error, (ValueError, RuntimeError)) else "No se pudo consultar Atlas"
        self.publicar(f"historial/respuesta/{identificador}", respuesta)

    def cerrar(self):
        if self.cliente:
            self.publicar("conexion", {"conectado": False}, retain=True)
            self.cliente.disconnect()
            self.cliente.loop_stop()
