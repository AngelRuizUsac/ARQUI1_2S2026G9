class GlobalState:

    _instance = None


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalState,cls).__new__(cls)
            cls._instance.inicializar()
        return cls._instance


    def inicializar(self):

        # Sensores
     
        self.temperatura = 0.0
        self.humedad = 0.0
        self.gas = 0
        self.distancia = 0.0
        self.luz = 0


        # Estado general

        self.estado_global = "NORMAL"


        # Actuadores

        self.ventilador = False
        self.alarma = False
        self.puerta = False
        self.luces = False
        self.modo_luces = "AUTOMATICO"


        # ARM64

        self.maximo = 0
        self.minimo = 0
        self.promedio = 0
        self.cantidad = 0


        # Sistema

        self.ultima_actualizacion = None
        self.error = ""


shared = GlobalState()