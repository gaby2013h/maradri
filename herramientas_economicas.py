##########################
# Agente Economico De IA #
# Herramientas           #
##########################

# Importacion para hacer llamados a APIs
import requests


class HerramientasEconomicas:

    # URL base de la API del Banco Mundial (no necesita autenticacion)
    URL_BANCO_MUNDIAL = "https://api.worldbank.org/v2/country/{pais}/indicator/{indicador}"

    def __init__(self):
        pass

    # Funcion auxiliar: consulta el dato mas reciente de un indicador del Banco Mundial.
    # La usan las herramientas de PIB, inflacion, desempleo, balanza y subalimentacion.
    def _consultar_banco_mundial(self, pais: str, indicador: str):
        url = self.URL_BANCO_MUNDIAL.format(pais=pais.strip().upper(), indicador=indicador)

        try:
            respuesta = requests.get(
                url,
                params={"format": "json", "mrnev": 1},  # mrnev=1 -> el dato mas reciente disponible
                timeout=30
            )
            respuesta.raise_for_status()
            datos = respuesta.json()

            if not isinstance(datos, list) or len(datos) < 2 or not datos[1]:
                return {"error": f"No se encontraron datos para el pais {pais}."}

            registro = datos[1][0]
            if registro["value"] is None:
                return {"error": "El registro no contiene un valor."}

            return {
                "pais": registro["country"]["value"],
                "anio": registro["date"],
                "valor": registro["value"],
            }

        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as e:
            print(f"Error al consultar el Banco Mundial ({indicador}, {pais}). Error: {e}")
            return {"error": "No se pudo consultar el Banco Mundial."}

    # Herramienta 1: PIB
    def consultar_pib(self, pais: str = "GTM"):
        print(f"Herramienta consultar_pib llamada con pais: {pais}")
        resultado = self._consultar_banco_mundial(pais, "NY.GDP.MKTP.CD")
        if "error" in resultado:
            return resultado
        return {
            "pais": resultado["pais"],
            "anio": resultado["anio"],
            "pib": resultado["valor"],
            "unidad": "USD corrientes",
            "fuente": "Banco Mundial (NY.GDP.MKTP.CD)",
        }

    # Herramienta 2: Inflacion
    def consultar_inflacion(self, pais: str = "GTM"):
        print(f"Herramienta consultar_inflacion llamada con pais: {pais}")
        resultado = self._consultar_banco_mundial(pais, "FP.CPI.TOTL.ZG")
        if "error" in resultado:
            return resultado
        return {
            "pais": resultado["pais"],
            "anio": resultado["anio"],
            "inflacion": round(float(resultado["valor"]), 2),
            "unidad": "% anual (precios al consumidor)",
            "fuente": "Banco Mundial (FP.CPI.TOTL.ZG)",
        }

    # Herramienta 3: Tipo de cambio (API open.er-api.com, sin autenticacion)
    def consultar_tipo_cambio(self, moneda: str):
        print(f"Herramienta consultar_tipo_cambio llamada con moneda: {moneda}")

        if not moneda:
            return {"error": "Se requiere el codigo de la moneda, por ejemplo USD."}

        url = f"https://open.er-api.com/v6/latest/{moneda.strip().upper()}"

        try:
            respuesta = requests.get(url, timeout=30)
            respuesta.raise_for_status()
            datos = respuesta.json()

            # La API devuelve TODAS las monedas; solo regresamos la tasa contra el quetzal
            # para no llenar al modelo con informacion que no necesita.
            tasa_gtq = datos.get("rates", {}).get("GTQ")
            if tasa_gtq is None:
                return {"error": f"No se encontro el tipo de cambio para {moneda}."}

            return {
                "moneda": moneda.upper(),
                "quetzales_por_unidad": tasa_gtq,
                "fecha_actualizacion": datos.get("time_last_update_utc"),
                "fuente": "open.er-api.com",
            }

        except (requests.RequestException, ValueError) as e:
            print(f"Error al consultar_tipo_cambio: {moneda}. Error: {e}")
            return {"error": f"No se pudo obtener el tipo de cambio para {moneda}."}

    # Herramienta 4: Desempleo
    def consultar_desempleo(self, pais: str = "GTM"):
        print(f"Herramienta consultar_desempleo llamada con pais: {pais}")
        resultado = self._consultar_banco_mundial(pais, "SL.UEM.TOTL.ZS")
        if "error" in resultado:
            return resultado
        return {
            "pais": resultado["pais"],
            "anio": resultado["anio"],
            "desempleo": round(float(resultado["valor"]), 2),
            "unidad": "% de la fuerza laboral",
            "fuente": "Banco Mundial, estimacion modelada de la OIT (SL.UEM.TOTL.ZS)",
        }

    # Herramienta 5: Balanza comercial de bienes
    def consultar_balanza_comercial(self, pais: str = "GTM"):
        print(f"Herramienta consultar_balanza_comercial llamada con pais: {pais}")
        resultado = self._consultar_banco_mundial(pais, "BN.GSR.MRCH.CD")
        if "error" in resultado:
            return resultado

        saldo = resultado["valor"]
        if saldo > 0:
            situacion = "superavit comercial"
        elif saldo < 0:
            situacion = "deficit comercial"
        else:
            situacion = "equilibrio comercial"

        return {
            "pais": resultado["pais"],
            "anio": resultado["anio"],
            "saldo": saldo,
            "situacion": situacion,
            "unidad": "USD corrientes",
            "fuente": "Banco Mundial (BN.GSR.MRCH.CD)",
        }

    # Herramienta 6 (extra): Prevalencia de subalimentacion
    def consultar_subalimentacion(self, pais: str = "GTM"):
        print(f"Herramienta consultar_subalimentacion llamada con pais: {pais}")
        resultado = self._consultar_banco_mundial(pais, "SN.ITK.DEFC.ZS")
        if "error" in resultado:
            return resultado
        return {
            "pais": resultado["pais"],
            "anio": resultado["anio"],
            "subalimentacion": round(float(resultado["valor"]), 2),
            "unidad": "% de la poblacion",
            "fuente": "Banco Mundial, datos de la FAO (SN.ITK.DEFC.ZS)",
        }
