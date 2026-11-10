
import json
import paho.mqtt.client as mqtt
from datetime import datetime

BROKER = "broker.hivemq.com"
PORTA = 1883
TOPICO = "highwater/ponto01/leituras"

ALTURA_LIMITE = 100

# Armazena a última leitura
leitura_anterior = None


def ao_conectar(cliente, userdata, flags, reason_code, properties):
    print("Conectado ao broker MQTT!")
    cliente.subscribe(TOPICO)


def ao_receber(cliente, userdata, mensagem):
    global leitura_anterior

    try:
        dados = json.loads(mensagem.payload.decode())

        nivel_atual = float(dados["nivel_agua_cm"])
        distancia = float(dados["distancia_cm"])
        ponto = dados["ponto_id"]

        timestamp = datetime.fromisoformat(dados["timestamp"])

        print("\n--- NOVA LEITURA ---")
        print(f"Ponto: {ponto}")
        print(f"Distância: {distancia} cm")
        print(f"Nível da água: {nivel_atual} cm")

        if leitura_anterior is not None:
            intervalo = (
                timestamp - leitura_anterior["timestamp"]
            ).total_seconds()

            if intervalo > 0:
                taxa = (
                    nivel_atual - leitura_anterior["nivel"]
                ) / intervalo

                print(f"Taxa de variação: {taxa:.2f} cm/s")

                if nivel_atual >= ALTURA_LIMITE:
                    risco = "CRITICO"
                elif taxa > 0 and nivel_atual >= 60:
                    risco = "ATENCAO"
                else:
                    risco = "NORMAL"

                print(f"Estado: {risco}")

                if taxa > 0 and nivel_atual < ALTURA_LIMITE:
                    tempo = (ALTURA_LIMITE - nivel_atual) / taxa
                    print(f"Tempo estimado até o limite: {tempo:.1f} s")

        leitura_anterior = {
            "nivel": nivel_atual,
            "timestamp": timestamp
        }

    except (ValueError, KeyError, TypeError) as erro:
        print("Mensagem inválida:", erro)


cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="highwater_backend_01"
)

cliente.on_connect = ao_conectar
cliente.on_message = ao_receber

cliente.connect(BROKER, PORTA, 60)

print("Aguardando mensagens MQTT...")
cliente.loop_forever()
