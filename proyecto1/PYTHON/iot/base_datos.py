from datetime import datetime, timezone

from pymongo import MongoClient

from configuracion import (
    MONGO_ACTIVO,
    MONGO_URI,
    MONGO_BASE_DATOS)



class BaseDatos:

    def __init__(self):
        self.activa = False
        self.cliente = None
        self.db = None

        if not MONGO_ACTIVO:

            print("MongoDB desactivado.")
            return



        try:

            self.cliente = MongoClient(MONGO_URI,serverSelectionTimeoutMS=5000)
            self.cliente.admin.command("ping")
            self.db = self.cliente[MONGO_BASE_DATOS]
            self.activa = True
            print("MongoDB conectado correctamente.")

        except Exception as error:

            print(f"Error conectando MongoDB: {error}")

    def guardar_lectura(self, datos):

        if not self.activa:
            return

        documento = datos.copy()

        documento["timestamp"] = datetime.now(timezone.utc)

        self.db.sensor_readings.insert_one(documento)


    def guardar_estado(self, estado):

        if not self.activa:
            return


        self.db.system_status.update_one(

            {"_id": "estado_actual"},
            {"$set":{"estado": estado,"timestamp":datetime.now(timezone.utc)}},

            upsert=True)


    def guardar_evento(self, tipo, mensaje):

        if not self.activa:
            return


        self.db.events.insert_one(

            {"tipo": tipo,"mensaje": mensaje,"timestamp":datetime.now(timezone.utc)})

    def guardar_comando(self, comando):

        if not self.activa:
            return

        documento = comando.copy()
        documento["timestamp"] = datetime.now(timezone.utc)

        self.db.commands.insert_one(documento)

    def guardar_resultado_arm64(self, resultado):
        if not self.activa:
            return


        documento = resultado.copy()
        documento["timestamp"] = datetime.now(timezone.utc)

        self.db.arm64_results.insert_one(documento)


    def obtener_ultimas_lecturas(self,cantidad=20):

        if not self.activa:
            return []

        datos = self.db.sensor_readings.find({}).sort("timestamp",-1).limit(cantidad)
        return list(datos)


    def obtener_eventos(self,cantidad=20):

        if not self.activa:
            return []

        datos = self.db.events.find({}).sort("timestamp",-1).limit(cantidad)
        return list(datos)


    def obtener_resultados_arm64(self,cantidad=20):

        if not self.activa:
            return []


        datos = self.db.arm64_results.find({}).sort("timestamp",-1).limit(cantidad)

        return list(datos)




    def cerrar(self):


        if self.cliente:

            self.cliente.close()