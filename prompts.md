# prompts.md
# Registro de Prompts — Projetos Python

## 1. Ferramenta utilizada

**Ferramenta:** ChatGPT (OpenAI)

**Finalidade:** Auxiliar no desenvolvimento de projetos Python, incluindo implementação, integração, simulação, processamento de dados e testes.

Este documento registra somente solicitações diretamente relacionadas ao desenvolvimento em Python. Brainstorming e propostas de projetos não são incluídos.

---

## 2. Histórico de prompts

### 2.1. Conversa: Ideia de projeto mobilidade

**Contexto:** Desenvolvimento independente da simulação em Python e do dispositivo ESP32.

**Prompt solicitado:**

> Como eu faria para simular os dados recebidos do ESP32 no Python para poder desenvolver ambos separadamente?

**Objetivo:**
Compreender como desenvolver e testar a parte Python independentemente do ESP32, utilizando dados simulados que representem as leituras que seriam recebidas do dispositivo.

**Aspectos abordados:**
- Simulação de dados de sensores em Python.
- Separação entre o desenvolvimento do ESP32 e do processamento em Python.
- Preparação para integração posterior entre os componentes.
- Utilização de dados simulados para testar o processamento antes da implementação física.

---

### 2.2. Conversa: Arquitetura FIWARE MQTT NGSI — comunicação MQTT com Python

**Contexto:** Comunicação entre dispositivos utilizando MQTT, com um ESP32 como publicador e um programa Python como assinante.

**Prompt solicitado:**

> E se o receptor for um código Python?

**Objetivo:**
Compreender como um programa Python pode receber mensagens publicadas por outro dispositivo através de um broker MQTT.

**Aspectos abordados:**
- Utilização da biblioteca Paho MQTT.
- Conexão de um cliente Python ao broker.
- Inscrição em tópicos MQTT utilizando `subscribe()`.
- Recepção de mensagens por meio de callbacks.
- Conversão do payload recebido de bytes para texto utilizando `decode("utf-8")`.

**Exemplo de implementação apresentado:**

```python
import paho.mqtt.client as mqtt

BROKER = "ENDERECO_DO_BROKER"
PORTA = 1883
TOPICO = "/projeto/sensores"

def ao_conectar(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Conectado ao broker!")
        client.subscribe(TOPICO)

def ao_receber(client, userdata, msg):
    texto = msg.payload.decode("utf-8")
    print("Mensagem recebida:", texto)

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = ao_conectar
client.on_message = ao_receber

client.connect(BROKER, PORTA, 60)
client.loop_forever()
```

---

### 2.3. Conversa atual: Recebimento e processamento de JSON via MQTT com Python

**Contexto:** Recebimento de mensagens JSON publicadas por um ESP32 e interpretação dos dados em Python.

**Prompt solicitado:**

> E se o receptor for um código Python?

**Objetivo:**
Adaptar o recebimento de mensagens MQTT para interpretar dados estruturados em JSON utilizando Python.

**Aspectos abordados:**
- Utilização da biblioteca nativa `json`.
- Conversão do payload recebido para texto.
- Utilização de `json.loads()` para transformar o JSON em um dicionário Python.
- Acesso aos valores por meio das chaves do dicionário.
- Utilização de `json.dumps()` para transformar dicionários Python em mensagens JSON.
- Possibilidade de utilizar Python tanto como assinante quanto como publicador MQTT.

**Exemplo de implementação apresentado:**

```python
import json
import paho.mqtt.client as mqtt

TOPICO = "/projeto/sensores"

def ao_receber(client, userdata, msg):
    try:
        texto = msg.payload.decode("utf-8")
        dados = json.loads(texto)

        temperatura = dados["temperatura"]
        umidade = dados["umidade"]
        luminosidade = dados["luminosidade"]

        print("Temperatura:", temperatura)
        print("Umidade:", umidade)
        print("Luminosidade:", luminosidade)

    except (json.JSONDecodeError, KeyError) as erro:
        print("Erro ao interpretar mensagem:", erro)
```

**Bibliotecas e recursos apresentados:**

| Biblioteca/recurso | Finalidade |
|---|---|
| `paho-mqtt` | Comunicação MQTT entre Python e o broker. |
| `json` | Serialização e desserialização de JSON. |
| `json.loads()` | Converter texto JSON em estruturas Python. |
| `json.dumps()` | Converter estruturas Python em texto JSON. |
| `decode("utf-8")` | Converter bytes recebidos em texto. |

---

## 3. Critérios para futuras atualizações

Serão incluídas novas solicitações quando estiverem diretamente relacionadas a tarefas de desenvolvimento em Python, como:

- Criação ou modificação de códigos Python.
- Integração de Python com ESP32, MQTT, React ou outras tecnologias.
- Simulação de dados e dispositivos.
- Processamento, armazenamento e análise de dados.
- Implementação de cálculos e algoritmos.
- Testes, depuração e correção de erros.
- Utilização de bibliotecas e ferramentas Python.

Não serão incluídas sugestões genéricas de projetos, brainstorming ou propostas de temas que apenas mencionem Python.

---

## 4. Observações

Os códigos apresentados são referências das soluções discutidas com a IA. Sua inclusão não significa necessariamente que tenham sido implementados ou validados integralmente no ambiente final do projeto.

O objetivo deste documento é registrar as solicitações realizadas e as funcionalidades técnicas discutidas como apoio ao desenvolvimento em Python.