
import time
from queue import Queue, Empty, Full
import configuracion as cfg
from sensores import enviar_ventilador


class Hardware:
    def __init__(self):
        self.dispositivos = []
        self.inicio_alarma = None
        self.comandos = Queue(maxsize=32)
        from gpiozero import LED, DigitalOutputDevice, PWMOutputDevice, Servo, Button
        pines = [*cfg.GPIO_LUCES, *cfg.GPIO_BOTONES, cfg.GPIO_SERVO,
                 cfg.GPIO_BUZZER, cfg.GPIO_VERDE, cfg.GPIO_AMARILLO, cfg.GPIO_ROJO,
                 cfg.GPIO_LED_PUERTA, cfg.GPIO_LED_VENTILADOR, cfg.DHT_GPIO, 2, 3]
        if len(pines) != len(set(pines)) or len(cfg.GPIO_BOTONES) != 4 or len(cfg.GPIO_LUCES) < 3:
            raise ValueError("Revisa GPIO: duplicados, menos de 3 luces o no hay 4 botones")
        def guardar(dispositivo):
            self.dispositivos.append(dispositivo)
            return dispositivo
        try:
            self.luces = [guardar(LED(p)) for p in cfg.GPIO_LUCES]
            self.buzzer = guardar(PWMOutputDevice(cfg.GPIO_BUZZER, initial_value=0,
                                                   frequency=cfg.BUZZER_FRECUENCIA))
            self.verde = guardar(LED(cfg.GPIO_VERDE))
            self.amarillo = guardar(LED(cfg.GPIO_AMARILLO))
            self.rojo = guardar(LED(cfg.GPIO_ROJO))
            self.puerta_led = guardar(LED(cfg.GPIO_LED_PUERTA))
            self.ventilador_led = guardar(LED(cfg.GPIO_LED_VENTILADOR))
            self.servo = guardar(Servo(cfg.GPIO_SERVO, initial_value=None,
                                min_pulse_width=cfg.SERVO_PULSO_MIN, max_pulse_width=cfg.SERVO_PULSO_MAX))
            for pin, tipo, accion in zip(cfg.GPIO_BOTONES,
                                        ("puerta", "modo_luces", "alarma", "estado"),
                                        ("alternar", "alternar", "silenciar", "restablecer")):
                boton = guardar(Button(pin, pull_up=True, bounce_time=0.15))
                boton.when_pressed = lambda t=tipo, a=accion: self.encolar(t, a)
        except BaseException:
            self.cerrar()
            raise

    def encolar(self, tipo, accion):
        try:
            self.comandos.put_nowait(dict(comando=tipo, accion=accion, origen="panel"))
        except Full:
            print("Panel: demasiadas pulsaciones pendientes")

    def obtener_comando(self):
        try:
            return self.comandos.get_nowait()
        except Empty:
            return None

    def aplicar(self, salidas, estado):
        for luz in self.luces:
            luz.value = salidas["luces"] == "ENCENDIDAS"
        encendido = salidas["ventilador"] == "ENCENDIDO"
        enviar_ventilador(encendido)
        self.ventilador_led.value = encendido
        if salidas["alarma"] == "ENCENDIDA":
            ahora = time.monotonic()
            if self.inicio_alarma is None:
                self.inicio_alarma = ahora

            fase = int((ahora - self.inicio_alarma) / 0.4) % 2
            frecuencia = cfg.BUZZER_FRECUENCIA if fase else max(1, cfg.BUZZER_FRECUENCIA // 2)
            if self.buzzer.frequency != frecuencia:
                self.buzzer.frequency = frecuencia
            self.buzzer.value = 0.5
        else:
            self.buzzer.value = 0
            self.inicio_alarma = None
        abierta = salidas["puerta"] == "ABIERTA"
        self.servo.value = cfg.SERVO_ABIERTO if abierta else cfg.SERVO_CERRADO
        self.puerta_led.value = abierta
        self.verde.value = estado == "NORMAL"
        self.amarillo.value = estado == "ADVERTENCIA"
        self.rojo.value = estado == "EMERGENCIA"

    def cerrar(self):
        enviar_ventilador(False, forzar=True)
        for dispositivo in reversed(self.dispositivos):
            try:
                if hasattr(dispositivo, "off"):
                    dispositivo.off()
            except Exception as error:
                print(f"Cierre GPIO: {error}")
            finally:
                try:
                    dispositivo.close()
                except Exception as error:
                    print(f"Liberacion GPIO: {error}")
        self.dispositivos.clear()
