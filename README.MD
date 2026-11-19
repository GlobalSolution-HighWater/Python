# High Water — Monitoramento IoT de Nível da Água

## Sobre o projeto

O **High Water** é um projeto acadêmico de Internet das Coisas (IoT) desenvolvido para demonstrar o monitoramento do nível da água em regiões suscetíveis a alagamentos.

A solução utiliza um ESP32 com sensor ultrassônico HC-SR04, comunicação MQTT e processamento de dados em Python. As leituras são armazenadas no Supabase, permitindo sua consulta por meio de um dashboard desenvolvido em React.

O projeto também conta com um simulador em Python para representar o funcionamento do dispositivo.

## Integrantes

Felipe Rabelo - RM 570340
Gustavo Ferreira Tavares - RM 569928
Ricardo Salmerón - RM 572916

## Dashboard

O projeto possui uma interface web desenvolvida em React e publicada na Vercel.

**Acesse:** [High Water — Simulação](https://front-web-rose.vercel.app/simulation)

## Arquitetura do projeto

```text
ESP32 + HC-SR04 (Wokwi)
          |
          v
      Broker MQTT
          |
          v
     Backend Python
          |
          v
       Supabase
          |
          v
    Dashboard React
```

- **Firmware:** código responsável pelo funcionamento do ESP32 e pela comunicação com o sensor ultrassônico.
- **Backend:** recebe as mensagens MQTT, processa as leituras e envia os registros ao Supabase.
- **Simulator:** simula o comportamento do dispositivo utilizando Python.
- **Supabase:** armazena os dados e disponibiliza uma API REST para consulta.
- **Dashboard:** apresenta os dados por meio de uma interface web.

## Estrutura de arquivos

```text
HighWater/
│
├── Backend/
│   ├── .env
│   ├── .env.example
│   └── receptor_mqtt.py
│
├── Firmware/
│   ├── diagram.json
│   ├── libraries.txt
│   ├── sketch.ino
│   └── wokwi-project.txt
│
├── Simulator/
│   └── simulador_esp32.py
│
├── .gitignore
├── prompts.md
└── README.md
```

### Backend

- `receptor_mqtt.py`: recebe e processa as mensagens MQTT.
- `.env`: armazena as credenciais de conexão com o Supabase.
- `.env.example`: disponibiliza um modelo das variáveis de ambiente necessárias.

### Firmware

- `sketch.ino`: código-fonte do ESP32.
- `diagram.json`: configuração dos componentes e conexões da simulação.
- `libraries.txt`: bibliotecas utilizadas pelo firmware.
- `wokwi-project.txt`: informações de configuração do projeto Wokwi.

### Simulator

- `simulador_esp32.py`: simula o comportamento do dispositivo e permite gerar leituras para o sistema.

## Hardware e simulação

O dispositivo utiliza:

- ESP32 DevKit.
- Sensor ultrassônico HC-SR04.
- Plataforma de simulação Wokwi.

### Diagrama do circuito — Wokwi

O circuito pode ser visualizado e executado diretamente na plataforma Wokwi:

<https://wokwi.com/projects/480232766107163649>

O projeto utiliza as seguintes conexões entre o HC-SR04 e o ESP32:

| HC-SR04 | ESP32 |
|---|---|
| VCC | 5V |
| TRIG | GPIO 25 |
| ECHO | GPIO 26 |
| GND | GND |

A altura de referência utilizada é de 150 cm.

O nível da água é calculado pela fórmula:

```python
nivel_agua_cm = altura_referencia_cm - distancia_cm
```

Como o sensor mede a distância até a superfície da água, uma distância menor representa um nível de água maior.

## Comunicação MQTT

O dispositivo publica as leituras em um broker MQTT utilizando as seguintes configurações:

```python
BROKER = "3.93.68.31"
PORTA = 1883
TOPICO = "highwater/ponto01/leituras"
```

O payload enviado pelo dispositivo utiliza o formato JSON:

```json
{
  "ponto_id": "ponto01",
  "timestamp": "2026-11-12T14:00:00Z",
  "distancia_cm": 70.0,
  "nivel_agua_cm": 80.0
}
```

O backend Python se inscreve no tópico para receber e processar as mensagens.

## Processamento dos dados

O backend utiliza a diferença entre duas leituras consecutivas para calcular a taxa de variação do nível da água.

A primeira derivada é aproximada numericamente por:

\[
H'(t) \approx \frac{H(t)-H(t-\Delta t)}{\Delta t}
\]

Onde:

- \(H(t)\): nível atual da água.
- \(H(t-\Delta t)\): nível da leitura anterior.
- \(\Delta t\): intervalo entre as medições.

A taxa é expressa em centímetros por segundo (cm/s).

- Taxa positiva: nível da água subindo.
- Taxa negativa: nível da água descendo.
- Taxa próxima de zero: nível aproximadamente estável.

### Classificação de risco

O projeto utiliza os seguintes limites demonstrativos:

| Estado | Condição |
|---|---|
| NORMAL | Nível abaixo de 60 cm, sem condição de atenção |
| ATENÇÃO | Nível a partir de 60 cm, com taxa positiva |
| CRÍTICO | Nível igual ou superior a 100 cm |

Esses valores são parâmetros utilizados na demonstração, não limites oficiais de segurança.

O backend também estima o tempo necessário para atingir o limite crítico, considerando a taxa de variação atual:

\[
tempo = \frac{nivel\_limite - nivel\_atual}{taxa}
\]

Essa estimativa é calculada quando a água está subindo e o nível ainda está abaixo do limite crítico. Ela considera que a taxa de variação permanecerá constante.

## Banco de dados e API — Supabase

O Supabase é utilizado como banco de dados PostgreSQL e disponibiliza automaticamente uma API REST para consultar os registros.

A tabela principal utilizada pelo projeto é `leituras`.

### Estrutura da tabela

| Coluna | Tipo | Descrição |
|---|---|---|
| id | bigint | Identificador do registro |
| ponto_id | text | Identificação do ponto monitorado |
| timestamp | timestamptz | Data e hora de registro |
| distancia_cm | float8 | Distância medida pelo sensor |
| nivel_agua_cm | float8 | Nível calculado da água |
| taxa_cm_por_s | float8 | Taxa de variação do nível |
| estado | text | Classificação de risco |

A coluna `timestamp` pode utilizar `DEFAULT NOW()` para registrar automaticamente o horário de inserção no banco.

### Consulta pela API REST

O endpoint segue o formato:

```text
https://SEU_PROJETO.supabase.co/rest/v1/leituras
```

O dashboard React pode consultar os registros utilizando `fetch()` e a chave pública do Supabase.

A chave secreta utilizada pelo backend Python não deve ser exposta no frontend.

## Configuração e execução

### Pré-requisitos

- Python instalado.
- Git instalado.
- Conta e projeto configurados no Supabase.
- Projeto do ESP32 configurado no Wokwi.

### 1. Clonar o repositório

```bash
git clone URL_DO_REPOSITORIO
cd HighWater
```

### 2. Configurar o backend

Entre na pasta `Backend`:

```bash
cd Backend
```

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

No Linux ou macOS:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install paho-mqtt supabase python-dotenv
```

### 3. Configurar as variáveis de ambiente

Na pasta `Backend`, utilize o arquivo `.env.example` como modelo.

Crie uma cópia com o nome `.env`:

```bash
copy .env.example .env
```

No Linux ou macOS:

```bash
cp .env.example .env
```

Preencha o arquivo `.env` com as credenciais do seu projeto Supabase:

```env
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_SECRET_KEY=SUA_CHAVE_SECRETA
```

### 4. Executar o backend

Com o ambiente virtual ativado e as variáveis configuradas:

```bash
python receptor_mqtt.py
```

O backend começará a aguardar mensagens publicadas no tópico MQTT configurado.

### 5. Executar o firmware no Wokwi

Abra o [projeto HighWater no Wokwi](https://wokwi.com/projects/480232766107163649) e inicie a simulação do ESP32.

### 6. Executar o simulador Python

Para utilizar o simulador alternativo, abra um terminal na pasta `Simulator` e execute:

```bash
python simulador_esp32.py
```

Caso o simulador utilize bibliotecas externas, instale as dependências necessárias antes de executá-lo.

## Segurança e versionamento

O arquivo `.gitignore`, localizado na raiz do projeto, deve impedir que arquivos privados e temporários sejam enviados ao GitHub.

Exemplo de configuração:

```gitignore
# Variáveis de ambiente
.env
.env.*
!.env.example

# Ambientes virtuais
venv/
.venv/

# Cache Python
__pycache__/
*.pyc
```

O arquivo `.env.example` permanece versionado, enquanto o `.env` e os ambientes virtuais ficam restritos à máquina local.

## Tecnologias utilizadas

- **C++ / Arduino:** programação do ESP32.
- **Wokwi:** simulação do hardware.
- **MQTT:** comunicação entre dispositivo e backend.
- **Python:** simulação, recepção e processamento dos dados.
- **Supabase / PostgreSQL:** armazenamento e disponibilização dos dados.
- **React:** desenvolvimento do dashboard.
- **Vercel:** publicação da aplicação web.

## Demonstração

- [Dashboard High Water](https://front-web-rose.vercel.app/simulation)
- [Circuito e simulação no Wokwi](https://wokwi.com/projects/480232766107163649)

**Observação:** para receber novas medições pelo fluxo completo, o dispositivo (Wokwi ou simulador Python) e o backend precisam estar em execução. Os registros já enviados permanecem armazenados no Supabase e podem ser consultados posteriormente.