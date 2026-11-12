
# ============================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ============================================================

import json  # Converte dados JSON recebidos em dicionários Python.
import os  # Permite acessar variáveis de ambiente do sistema.
import paho.mqtt.client as mqtt  # Biblioteca responsável pela comunicação MQTT.
from supabase import Client, create_client  # Permite conectar e interagir com o Supabase.
from dotenv import load_dotenv  # Carrega variáveis de ambiente armazenadas no arquivo .env.
from datetime import datetime  # Permite interpretar e manipular datas e horários.


# ============================================================
# CARREGAMENTO DAS CONFIGURAÇÕES
# ============================================================

# Carrega as variáveis definidas no arquivo .env para o ambiente Python.
load_dotenv()

# Endereço IP do broker MQTT responsável por distribuir as mensagens.
BROKER = "3.93.68.31"

# Porta utilizada para estabelecer a conexão MQTT.
PORTA = 1883

# Tópico MQTT no qual o ESP32 publica as leituras do sensor.
TOPICO = "highwater/ponto01/leituras"


# ============================================================
# CONFIGURAÇÃO DO SUPABASE
# ============================================================

# Recupera o endereço do projeto Supabase armazenado no arquivo .env.
SUPABASE_URL = os.getenv("SUPABASE_URL")

# Recupera a chave secreta de acesso ao Supabase.
# Essa chave deve permanecer privada e nunca ser compartilhada no frontend.
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

# Cria a conexão com o projeto Supabase.
# O objeto supabase será utilizado para inserir os dados no banco.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# PARÂMETROS DO SISTEMA
# ============================================================

# Nível da água considerado crítico, medido em centímetros.
ALTURA_LIMITE = 100

# Armazena as informações da leitura anterior.
# Inicialmente recebe None porque ainda não existem leituras anteriores.
leitura_anterior = None


# ============================================================
# CALLBACK DE CONEXÃO MQTT
# ============================================================

# Esta função é executada automaticamente quando o cliente MQTT
# estabelece uma conexão com o broker.
def ao_conectar(cliente, userdata, flags, reason_code, properties):

    print("Conectado ao broker MQTT!")

    # Inscreve o cliente no tópico para começar a receber as mensagens.
    cliente.subscribe(TOPICO)


# ============================================================
# CALLBACK DE RECEBIMENTO DE MENSAGENS MQTT
# ============================================================

# Esta função é executada automaticamente sempre que uma nova
# mensagem chega pelo tópico MQTT inscrito.
def ao_receber(cliente, userdata, mensagem):

    # Permite acessar e atualizar a variável global entre as chamadas.
    global leitura_anterior

    try:
        # Decodifica os bytes recebidos e converte o JSON em um dicionário Python.
        dados = json.loads(mensagem.payload.decode())

        # Extrai o nível atual da água e converte o valor para float.
        nivel_atual = float(dados["nivel_agua_cm"])

        # Extrai a distância medida pelo sensor ultrassônico.
        distancia = float(dados["distancia_cm"])

        # Identifica o ponto de monitoramento responsável pela leitura.
        ponto = dados["ponto_id"]

        # Converte o timestamp recebido em uma estrutura de data e horário.
        timestamp = datetime.fromisoformat(dados["timestamp"])

        # Exibe as informações básicas da leitura recebida.
        print("\n--- NOVA LEITURA ---")
        print(f"Ponto: {ponto}")
        print(f"Distância: {distancia} cm")
        print(f"Nível da água: {nivel_atual} cm")


        # ====================================================
        # CÁLCULO DA PRIMEIRA DERIVADA
        # ====================================================

        # Verifica se existe uma leitura anterior para realizar a comparação.
        if leitura_anterior is not None:

            # Calcula o intervalo de tempo entre as duas medições, em segundos.
            intervalo = (
                timestamp - leitura_anterior["timestamp"]
            ).total_seconds()

            # Evita divisões por zero ou intervalos de tempo negativos.
            if intervalo > 0:

                # Calcula a taxa de variação do nível da água.
                # É uma aproximação numérica da primeira derivada:
                # ΔH / Δt, expressa em centímetros por segundo.
                taxa = (
                    nivel_atual - leitura_anterior["nivel"]
                ) / intervalo

                print(f"Taxa de variação: {taxa:.2f} cm/s")


                # ============================================
                # CLASSIFICAÇÃO DO NÍVEL DE RISCO
                # ============================================

                # Se o nível atingir ou ultrapassar o limite,
                # o estado do ponto será considerado crítico.
                if nivel_atual >= ALTURA_LIMITE:
                    risco = "CRITICO"

                # Se a água estiver subindo e atingir 60 cm,
                # o sistema classifica a situação como atenção.
                elif taxa > 0 and nivel_atual >= 60:
                    risco = "ATENCAO"

                # Caso nenhuma das condições anteriores seja atendida,
                # o estado será considerado normal.
                else:
                    risco = "NORMAL"

                print(f"Estado: {risco}")


                # ============================================
                # PREVISÃO DE TEMPO ATÉ O LIMITE
                # ============================================

                # Só realiza a previsão se o nível estiver subindo
                # e ainda não tiver atingido o limite crítico.
                if taxa > 0 and nivel_atual < ALTURA_LIMITE:

                    # Estima quanto tempo falta para atingir o limite,
                    # considerando que a taxa de subida permaneça constante.
                    tempo = (ALTURA_LIMITE - nivel_atual) / taxa

                    print(f"Tempo estimado até o limite: {tempo:.1f} s")


        # ====================================================
        # ATUALIZAÇÃO DA LEITURA ANTERIOR
        # ====================================================

        # Armazena os dados atuais para que possam ser comparados
        # com a próxima medição recebida.
        leitura_anterior = {
            "nivel": nivel_atual,
            "timestamp": timestamp
        }


        # ====================================================
        # ENVIO DOS DADOS AO SUPABASE
        # ====================================================

        # Insere uma nova linha na tabela "leituras" do banco de dados.
        # O timestamp pode ser preenchido automaticamente pelo Supabase,
        # caso a coluna tenha DEFAULT NOW() configurado.
        supabase.table("leituras").insert({

            # Identificação do ponto de monitoramento.
            "ponto_id": ponto,

            # Nível atual da água, em centímetros.
            "nivel_agua_cm": nivel_atual,

            # Distância entre o sensor e a superfície da água.
            "distancia_cm": distancia,

            # Taxa de variação calculada, caso exista uma leitura anterior.
            # Caso contrário, o campo receberá None (NULL no banco).
            "taxa_cm_por_s": f"{taxa:.2f}" if 'taxa' in locals() else None,

            # Estado de risco calculado.
            # Na primeira leitura, utiliza NORMAL como valor inicial.
            "estado": risco if 'risco' in locals() else "NORMAL",

        }).execute()  # Executa efetivamente a inserção no banco de dados.


    # Captura erros relacionados à leitura e conversão dos dados recebidos.
    except (ValueError, KeyError, TypeError) as erro:

        print("Mensagem inválida:", erro)


# ============================================================
# CONFIGURAÇÃO DO CLIENTE MQTT
# ============================================================

# Cria um cliente MQTT utilizando a versão 2 da API de callbacks do Paho.
# O client_id identifica este cliente perante o broker.
cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="highwater_backend_01"
)

# Define qual função será executada quando houver uma conexão MQTT.
cliente.on_connect = ao_conectar

# Define qual função será executada quando uma mensagem for recebida.
cliente.on_message = ao_receber


# ============================================================
# INICIALIZAÇÃO DO SISTEMA
# ============================================================

# Estabelece a conexão com o broker MQTT.
cliente.connect(BROKER, PORTA, 60)

# Exibe uma mensagem indicando que o sistema está aguardando leituras.
print("Aguardando mensagens MQTT...")

# Mantém o cliente MQTT em execução continuamente,
# aguardando novas mensagens e executando os callbacks automaticamente.
cliente.loop_forever()
