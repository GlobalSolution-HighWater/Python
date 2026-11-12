
import json
import time
from datetime import datetime, timezone, timedelta

import paho.mqtt.client as mqtt

# Configuração MQTT
BROKER = "3.93.68.31"
PORTA = 1883
TOPICO = "highwater/ponto01/leituras"

# Configuração do sensor simulado
ALTURA_REFERENCIA = 150
INTERVALO = 3

# Sequência de distâncias simulando a subida da água
distancias = [
    140, 135, 130, 120, 110,
    100, 90, 80, 70, 60, 50
]

cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="highwater_simulador_01"
)

cliente.connect(BROKER, PORTA, 60)
cliente.loop_start()

try:
    while True:
        for distancia in distancias:

            nivel = ALTURA_REFERENCIA - distancia

            mensagem = {
                "ponto_id": "ponto01",
                "timestamp": datetime.now(
                    timezone(timedelta(hours=-3))
                ).isoformat(),
                "distancia_cm": distancia,
                "nivel_agua_cm": nivel
            }

            cliente.publish(
                TOPICO,
                json.dumps(mensagem),
                qos=0
            )

            print("Enviado:", mensagem)

            time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\nSimulador encerrado.")

finally:
    cliente.loop_stop()
    cliente.disconnect()
