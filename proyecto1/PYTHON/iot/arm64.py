
import subprocess
from configuracion import RUTA_ARM64, BINARIO_ARM64, LECTURAS_ARM64

temperaturas = []


def agregar_temperatura(temperatura):

    if not isinstance(temperatura, (int, float)) or not 0 <= temperatura <= 1000:
        return None
    if len(temperaturas) < LECTURAS_ARM64:
        temperaturas.append(int(round(temperatura)))
    if len(temperaturas) < LECTURAS_ARM64:
        return None
    resultado = procesar_con_arm64(temperaturas[:LECTURAS_ARM64])
    if resultado is not None:
        del temperaturas[:LECTURAS_ARM64]
    return resultado


def generar_datos_txt(lecturas):
    if not lecturas or any(type(x) is not int or not 0 <= x <= 1000 for x in lecturas):
        raise ValueError("Entrada ARM64: enteros de 0 a 1000")
    texto = "".join(f"{x}\n" for x in lecturas) + "$\n"
    if len(texto.encode("ascii")) >= 1024:
        raise ValueError("Entrada ARM64 demasiado grande (maximo 1023 bytes)")
    ruta = RUTA_ARM64 / "datos.txt"
    ruta.write_text(texto, encoding="ascii")
    return ruta


def procesar_con_arm64(lecturas):
    try:
        generar_datos_txt(lecturas)
        binario = RUTA_ARM64 / BINARIO_ARM64
        if not binario.is_file():
            print("ARM64: ejecutar make en proyecto1/ARM64; lote conservado para reintento")
            return None

        (RUTA_ARM64 / "resultado.txt").unlink(missing_ok=True)
        subprocess.run([str(binario)], cwd=RUTA_ARM64, check=True, timeout=10)
        resultado = leer_resultado()
        if resultado["cantidad"] != len(lecturas):
            raise ValueError("ARM64 devolvio una cantidad distinta al lote")
        return resultado
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ARM64: {error}; lote conservado para reintento")
        return None


def leer_resultado():
    campos = {"MAX": "maximo", "MIN": "minimo", "AVG": "promedio", "COUNT": "cantidad"}
    resultado = {}
    for linea in (RUTA_ARM64 / "resultado.txt").read_text(encoding="ascii").splitlines():
        clave, separador, valor = linea.partition("=")
        if separador != "=" or clave not in campos or campos[clave] in resultado:
            raise ValueError("Formato ARM64 invalido")
        resultado[campos[clave]] = int(valor)
    if set(resultado) != set(campos.values()):
        raise ValueError("Salida ARM64 incompleta")
    if not 0 <= resultado["minimo"] <= resultado["promedio"] <= resultado["maximo"] <= 1000 or resultado["cantidad"] <= 0:
        raise ValueError("Salida ARM64 inconsistente")
    return resultado
