import random
from datetime import datetime
from configuracion import MODO_SIMULACION
from Globals import shared



def leer_sensores():
    
    
    # Está funcionando con valores simulados

    if MODO_SIMULACION:
        leer_sensores_simulados()
    else:
        leer_sensores_reales()



def leer_sensores_simulados():
    
    # Genera datos de prueba simulando sensores reales

    shared.temperatura = round(random.uniform(20, 35),1)
    shared.humedad = round(random.uniform(35, 80),1)
    shared.gas = random.randint(100,1000)
    shared.distancia = round(random.uniform(5, 100),1)
    shared.luz = random.randint(0,100)
    shared.ultima_actualizacion = datetime.now()



def leer_sensores_reales():
    
    #Acá va la lectura real de los GPIO 

    raise Exception("Sensores reales no configurados todavía.")