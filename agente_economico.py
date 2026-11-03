##########################
# Agente Economico De IA #
# Agente                 #
##########################

# Importacion para el ambiente
from dotenv import load_dotenv

# Importacion para el LLM
from groq import Groq

# Importacion para el manejo de sistema
import os

# Importacion para el uso de formato JSON
import json

# Importacion para el manejo de fechas y zonas horarias
from datetime import datetime
from zoneinfo import ZoneInfo

# Importacion para el manejo memoria y herramientas
from basic_memory import BasicMemory
from herramientas_economicas import HerramientasEconomicas


# Cargar variables de entorno
load_dotenv()

# Inicializar el cliente de Groq con la clave de API
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

# Captura la hora actual en la zona horaria de Guatemala
now = datetime.now(ZoneInfo("America/Guatemala"))

# Inicializar herramientas y memoria
MEMORY_MAX_MESSAGES = 10
memory = BasicMemory(max_messages=MEMORY_MAX_MESSAGES)
herramientas = HerramientasEconomicas()


###############################################
# 1. CEREBRO: SYSTEM_PROMPT con rol y objetivo #
###############################################
SYSTEM_PROMPT = f"""
Eres un agente economico especializado en la economia de Guatemala. Hablas en español
y respondes de forma clara, breve y profesional.

Objetivo:
Proporcionar analisis economicos precisos, comparativos y actualizados que apoyen
la toma de decisiones, usando datos oficiales obtenidos con tus herramientas.

Fecha y hora actual en Guatemala: {now.strftime("%d/%m/%Y %H:%M")}.

Herramientas disponibles:
- consultar_pib: PIB en USD corrientes de un pais.
- consultar_inflacion: inflacion anual (% de precios al consumidor) de un pais.
- consultar_tipo_cambio: cuantos quetzales vale una unidad de otra moneda.
- consultar_desempleo: tasa de desempleo (% de la fuerza laboral) de un pais.
- consultar_balanza_comercial: saldo de la balanza comercial de bienes de un pais.
- consultar_subalimentacion: % de la poblacion con subalimentacion en un pais.

Reglas:
- Siempre usa las herramientas para obtener cifras; nunca inventes datos.
- Los paises se envian con su codigo ISO de 3 letras (Guatemala = GTM, Mexico = MEX,
  El Salvador = SLV, Honduras = HND, Estados Unidos = USA). Si el usuario no indica
  pais, asume Guatemala (GTM).
- Las monedas se envian con su codigo de 3 letras (USD, EUR, MXN...).
- Si el usuario pide comparar paises, llama a la herramienta una vez por cada pais.
- Indica siempre el año del dato y la fuente.
- Despues de dar la cifra, agrega una interpretacion economica breve (1 o 2 oraciones).
- Si una herramienta devuelve un error, informalo al usuario sin inventar el dato.
"""


#############################################################
# 3. HERRAMIENTAS: definicion que el modelo puede ver (TOOLS) #
#############################################################

# Parametro "pais" que comparten las herramientas del Banco Mundial
PARAMETRO_PAIS = {
    "type": "object",
    "properties": {
        "pais": {
            "type": "string",
            "description": "Codigo ISO de 3 letras del pais, por ejemplo GTM para Guatemala"
        }
    },
    "required": ["pais"]
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_pib",
            "description": "Consulta el PIB mas reciente (USD corrientes) de un pais segun el Banco Mundial.",
            "parameters": PARAMETRO_PAIS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_inflacion",
            "description": "Consulta la inflacion anual mas reciente (% precios al consumidor) de un pais segun el Banco Mundial.",
            "parameters": PARAMETRO_PAIS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_tipo_cambio",
            "description": "Consulta cuantos quetzales de Guatemala equivalen a una unidad de la moneda indicada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "moneda": {
                        "type": "string",
                        "description": "Codigo de la moneda que se desea consultar, por ejemplo USD"
                    }
                },
                "required": ["moneda"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_desempleo",
            "description": "Consulta la tasa de desempleo mas reciente (% de la fuerza laboral) de un pais segun el Banco Mundial.",
            "parameters": PARAMETRO_PAIS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_balanza_comercial",
            "description": "Consulta el saldo mas reciente de la balanza comercial de bienes (USD) de un pais e indica si hay deficit o superavit.",
            "parameters": PARAMETRO_PAIS
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_subalimentacion",
            "description": "Consulta la prevalencia de subalimentacion (% de la poblacion) de un pais segun el Banco Mundial.",
            "parameters": PARAMETRO_PAIS
        }
    }
]


#########################################################
# Ejecuta la herramienta que el modelo decidio llamar    #
#########################################################
def ejecutar_herramienta(name: str, args: dict):
    pais = args.get("pais", "GTM")

    if name == "consultar_pib":
        return herramientas.consultar_pib(pais=pais)
    elif name == "consultar_inflacion":
        return herramientas.consultar_inflacion(pais=pais)
    elif name == "consultar_tipo_cambio":
        return herramientas.consultar_tipo_cambio(moneda=args.get("moneda", ""))
    elif name == "consultar_desempleo":
        return herramientas.consultar_desempleo(pais=pais)
    elif name == "consultar_balanza_comercial":
        return herramientas.consultar_balanza_comercial(pais=pais)
    elif name == "consultar_subalimentacion":
        return herramientas.consultar_subalimentacion(pais=pais)
    else:
        print(f"Se intentó llamar a una herramienta desconocida {name}")
        return {"error": f"Herramienta desconocida: {name}"}


print("Agente Economico De IA (escribe 'salir' para terminar)")


def process_response(client: Groq, memory_messages: list[dict], user_text: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory_messages)
    messages.append({"role": "user", "content": user_text})

    while True:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=TOOLS
        )

        msg = resp.choices[0].message

        # Si no hay llamados a herramientas, entonces ya regresamos la respuesta
        if not getattr(msg, "tool_calls", None):
            return msg.content or ""

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls]
        })

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            result = ejecutar_herramienta(name, args)

            # Agregar a los mensajes el resultado del llamado de la herramienta
            # Esto lo recibirá el modelo al continuar la iteración
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })


if __name__ == "__main__":
    while True:

        user_text = input("Tú: ").strip()
        if not user_text:
            continue

        if user_text.lower() in ("exit", "salir"):
            print("Hasta luego!")
            break

        assistant_text = process_response(client, memory.messages(), user_text)
        print(f"Agente: {assistant_text}")

        # 2. MEMORIA: actualizar la memoria
        memory.add("user", user_text)
        memory.add("assistant", assistant_text)
