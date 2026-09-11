
import time
from configuracion import TEMPERATURA_MAXIMA, LUZ_MINIMA, DISTANCIA_PUERTA, PUERTA_SEGUNDOS
from estado import obtener_estado


def normalizar_comando(comando):
    if not isinstance(comando, dict):
        raise ValueError("Se esperaba un objeto JSON")
    tipo = comando.get("comando", comando.get("command", comando.get("action")))
    accion = comando.get("accion", comando.get("value", comando.get("action")))
    if not isinstance(tipo, str) or not isinstance(accion, str):
        raise ValueError("Comando y accion deben ser texto")
    return tipo.lower(), accion.lower()


class Controlador:
    def __init__(self, reloj=time.monotonic):
        self.reloj = reloj
        self.datos = {}
        self.emergencia = False
        self.silenciada = False
        self.cierre = 0
        self.cerca_anterior = False
        self.ventilador_manual = None
        self.estado = "NORMAL"
        self.salidas = dict(puerta="CERRADA", luces="APAGADAS", modo_luces="AUTOMATICO",
                            ventilador="APAGADO", alarma="APAGADA")

    def actualizar(self, datos=None):
        if datos is not None:
            self.datos = datos
        base = obtener_estado(self.datos)
        if base == "EMERGENCIA":
            if not self.emergencia:
                self.silenciada = False
            self.emergencia = True
        self.estado = "EMERGENCIA" if self.emergencia else base
        cerca = self.datos.get("distancia") is not None and self.datos["distancia"] < DISTANCIA_PUERTA

        if cerca and not self.cerca_anterior and not self.emergencia:
            self.cierre = self.reloj() + PUERTA_SEGUNDOS
        self.cerca_anterior = cerca
        self.salidas["puerta"] = "ABIERTA" if self.emergencia or self.reloj() < self.cierre else "CERRADA"
        temp = self.datos.get("temperatura")
        caliente = temp is not None and temp > TEMPERATURA_MAXIMA
        self.salidas["ventilador"] = "ENCENDIDO" if caliente or self.ventilador_manual is True else "APAGADO"
        self.salidas["alarma"] = "ENCENDIDA" if self.emergencia and not self.silenciada else "APAGADA"
        if self.salidas["modo_luces"] == "AUTOMATICO":
            luz = self.datos.get("luz")
            self.salidas["luces"] = "ENCENDIDAS" if luz is not None and luz < LUZ_MINIMA else "APAGADAS"
        return self.salidas.copy()

    def ejecutar(self, comando):
        try:
            tipo, accion = normalizar_comando(comando)
            if tipo == "puerta" and accion in ("abrir", "cerrar", "alternar"):
                if accion == "alternar":
                    accion = "cerrar" if self.salidas["puerta"] == "ABIERTA" else "abrir"
                if accion == "cerrar" and self.emergencia:
                    raise ValueError("La puerta permanece abierta durante la emergencia")
                self.cierre = self.reloj() + PUERTA_SEGUNDOS if accion == "abrir" else 0
            elif tipo == "luces" and accion in ("encender", "apagar"):
                self.salidas["modo_luces"] = "MANUAL"
                self.salidas["luces"] = "ENCENDIDAS" if accion == "encender" else "APAGADAS"
            elif tipo in ("modo_luces", "luces") and accion in ("automatico", "manual", "alternar"):
                if accion == "alternar":
                    accion = "manual" if self.salidas["modo_luces"] == "AUTOMATICO" else "automatico"
                self.salidas["modo_luces"] = accion.upper()
            elif tipo == "ventilador" and accion in ("encender", "apagar", "automatico"):
                if accion == "apagar" and (self.datos.get("temperatura") or 0) > TEMPERATURA_MAXIMA:
                    raise ValueError("Temperatura alta: ventilacion automatica obligatoria")
                self.ventilador_manual = None if accion == "automatico" else accion == "encender"
            elif tipo == "alarma" and accion == "silenciar":
                self.silenciada = True
            elif tipo == "estado" and accion == "restablecer":
                gas = self.datos.get("gas")
                if type(gas) is not int or not 0 <= gas <= 1023 or obtener_estado(self.datos) == "EMERGENCIA":
                    raise ValueError("No se puede restablecer: gas peligroso o sin lectura")
                self.emergencia = False
                self.silenciada = False
            else:
                raise ValueError("Comando o accion no reconocidos")
            self.actualizar()
            return dict(aceptado=True, mensaje="Ejecutado", comando=tipo, accion=accion)
        except ValueError as error:
            return dict(aceptado=False, mensaje=str(error))
