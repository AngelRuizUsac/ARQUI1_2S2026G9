
from datetime import datetime, timezone
from queue import Queue, Empty, Full
from threading import Thread, Event
from configuracion import MONGO_ACTIVO, MONGO_URI, MONGO_BASE_DATOS

COLECCIONES = {"sensor_readings", "events", "commands", "arm64_results", "system_status"}


class BaseDatos:
    def __init__(self):
        self.activa = MONGO_ACTIVO
        self.cliente = None
        self.base_datos = None
        self.cola = Queue(maxsize=2000)
        self.fin = Event()
        self.hilo = None
        if not self.activa:
            print("MongoDB desactivado: no se guarda historial persistente.")
            return
        from pymongo import MongoClient
        self.cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500,
                                   connectTimeoutMS=1500, socketTimeoutMS=1500)
        self.base_datos = self.cliente[MONGO_BASE_DATOS]
        self.hilo = Thread(target=self._trabajar, daemon=True)
        self.hilo.start()

    def _encolar(self, coleccion, documento, estado=False):
        if not self.activa:
            return
        from bson import ObjectId
        documento = {**documento, "timestamp": datetime.now(timezone.utc)}
        documento["_id"] = "estado_actual" if estado else ObjectId()
        try:
            self.cola.put_nowait((coleccion, documento))
        except Full:
            print("MongoDB: cola llena (2000); registro descartado. Revisar conexion.")

    def _trabajar(self):
        pendiente = None
        while not self.fin.is_set():
            if pendiente is None:
                try:
                    pendiente = self.cola.get(timeout=0.2)
                except Empty:
                    continue
            nombre, documento = pendiente
            try:

                self.base_datos[nombre].replace_one({"_id": documento["_id"]}, documento, upsert=True)
                self.cola.task_done()
                pendiente = None
            except Exception as error:
                print(f"MongoDB: reintento pendiente ({type(error).__name__})")
                self.fin.wait(3)

    def guardar_lectura(self, datos):
        self._encolar("sensor_readings", datos)

    def guardar_evento(self, tipo, mensaje):
        self._encolar("events", dict(tipo=tipo, mensaje=mensaje))

    def guardar_comando(self, comando):
        self._encolar("commands", comando)

    def guardar_estado(self, estado):
        self._encolar("system_status", dict(estado=estado), estado=True)

    def guardar_resultado_arm64(self, resultado):
        self._encolar("arm64_results", resultado)

    def historial(self, coleccion, limite=40):
        if coleccion not in COLECCIONES:
            raise ValueError("Coleccion no permitida")
        if not self.activa:
            raise RuntimeError("MongoDB desactivado")
        limite = max(1, min(int(limite), 200))
        docs = list(self.base_datos[coleccion].find({}, {"_id": 0}).sort("timestamp", -1).limit(limite))
        for doc in docs:
            if isinstance(doc.get("timestamp"), datetime):
                doc["timestamp"] = doc["timestamp"].replace(tzinfo=timezone.utc).isoformat()
        return docs

    def cerrar(self):
        if self.hilo:

            import time
            limite = time.monotonic() + 3
            while self.cola.unfinished_tasks and time.monotonic() < limite:
                time.sleep(0.05)
            if self.cola.unfinished_tasks:
                print(f"MongoDB: {self.cola.unfinished_tasks} registros pendientes al cerrar; no persistidos")
            self.fin.set()
            self.hilo.join(timeout=2)
        if self.cliente:
            self.cliente.close()
