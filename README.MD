# HighWater — Sistema IoT de Monitoramento de Nível de Água

## 1. Sobre o projeto

O **HighWater** é um sistema de monitoramento de nível de água desenvolvido como projeto acadêmico. Seu objetivo é demonstrar como tecnologias de Internet das Coisas (IoT), processamento de dados e desenvolvimento web podem ser utilizadas para monitorar situações de possível alagamento.

O projeto utiliza um ESP32 simulado no Wokwi, comunicação MQTT, processamento de dados em Python e armazenamento em nuvem por meio do Supabase.

## 2. Problema

Alagamentos representam um problema recorrente em grandes centros urbanos, como São Paulo. A elevação do nível da água pode acontecer rapidamente, dificultando a identificação antecipada de situações de risco.

A ausência de monitoramento contínuo dificulta a identificação de mudanças no nível da água e a emissão de alertas preventivos.

O HighWater propõe uma demonstração de como sensores e processamento automatizado podem auxiliar nesse monitoramento.

## 3. Solução proposta

O sistema utiliza um sensor ultrassônico HC-SR04 conectado a um ESP32 simulado no Wokwi para representar o monitoramento de um ponto sujeito a alagamentos.

O sensor mede a distância entre sua posição fixa e a superfície da água. A partir dessa distância, o sistema calcula o nível da água utilizando uma altura de referência.

O Python recebe as medições por MQTT e realiza o processamento dos dados, incluindo:

- Cálculo da taxa de variação do nível da água por meio da primeira derivada.
- Identificação da tendência de subida ou descida da água.
- Classificação do estado do ponto monitorado.
- Estimativa do tempo necessário para atingir o limite crítico, considerando a taxa de subida atual.

Após o processamento, os resultados são enviados ao Supabase, que armazena os registros e disponibiliza uma API REST para consulta pelo Dashboard desenvolvido em React.

## 4. Arquitetura do sistema

O funcionamento do projeto pode ser dividido em cinco etapas:

1. **Wokwi e ESP32:** simulam o dispositivo IoT e realizam as medições do sensor ultrassônico.
2. **MQTT:** transporta as mensagens publicadas pelo ESP32 até o receptor Python.
3. **Python:** recebe as medições, calcula as derivadas, classifica os riscos e prepara os dados.
4. **Supabase:** armazena os registros em um banco PostgreSQL e disponibiliza uma API REST.
5. **React:** consulta os dados armazenados e apresenta as informações ao usuário por meio de um Dashboard.

### Fluxo de comunicação

```text
       WOKWI
    ESP32 + HC-SR04
          |
          | Publicação MQTT
          v
      BROKER MQTT
          |
          | Recebimento MQTT
          v
     PYTHON BACKEND
    - Processamento
    - Cálculo da derivada
    - Classificação de risco
    - Previsão de tempo
          |
          | Inserção de registros
          v
       SUPABASE
    - Banco PostgreSQL
    - API REST
          |
          | Consulta HTTP
          v
    DASHBOARD REACT
```

## 5. Integração com o Wokwi e o MQTT

### 5.1. Simulação do dispositivo

O Wokwi é utilizado para simular o ESP32 e o sensor ultrassônico HC-SR04.

O sensor mede a distância entre ele e a superfície da água. Quando a água sobe, essa distância diminui.

Para transformar a distância em nível de água, é utilizada a seguinte fórmula:

```python
nivel_agua_cm = altura_referencia_cm - distancia_cm
```

No projeto, a altura de referência utilizada como exemplo é de 150 cm.

Assim, se o sensor medir uma distância de 70 cm, o nível calculado será:

```text
150 - 70 = 80 cm
```

### 5.2. Comunicação MQTT

O MQTT é um protocolo de comunicação baseado no modelo Publisher/Subscriber.

Nesse modelo:

- O ESP32 atua como Publisher, publicando as medições.
- O broker MQTT recebe e distribui as mensagens.
- O Python atua como Subscriber, recebendo as informações publicadas.

Configurações utilizadas pelo projeto:

| Parâmetro | Valor |
|---|---|
| Broker | `3.93.68.31` |
| Porta | `1883` |
| Tópico | `highwater/ponto01/leituras` |

O ESP32 publica as leituras no tópico configurado, enquanto o Python permanece inscrito nesse mesmo tópico aguardando novas mensagens.

### 5.3. Formato das mensagens

As informações são transmitidas em formato JSON.

Exemplo:

```json
{
  "ponto_id": "ponto01",
  "timestamp": "2026-11-12T14:00:00Z",
  "distancia_cm": 70.0,
  "nivel_agua_cm": 80.0
}
```

Cada mensagem contém:

- `ponto_id`: identificação do ponto monitorado.
- `timestamp`: horário em que a medição foi realizada.
- `distancia_cm`: distância medida pelo sensor.
- `nivel_agua_cm`: nível de água calculado pelo ESP32.

O Python interpreta o JSON recebido e extrai as informações necessárias para realizar os cálculos.

**Importante:** o endereço do broker e o tópico precisam ser iguais no firmware do ESP32 e no programa Python.

## 6. Processamento dos dados em Python

O Python é responsável por receber as medições MQTT e realizar os cálculos utilizados pelo sistema.

### 6.1. Cálculo da primeira derivada

A primeira derivada representa a taxa de variação do nível da água em relação ao tempo.

Como as medições são discretas, o projeto utiliza uma aproximação numérica por diferenças finitas:

\[
H'(t) \approx \frac{H(t)-H(t-\Delta t)}{\Delta t}
\]

Onde:

- \(H(t)\): nível atual da água.
- \(H(t-\Delta t)\): nível da medição anterior.
- \(\Delta t\): intervalo de tempo entre as medições.

O resultado é expresso em centímetros por segundo (cm/s).

Interpretação:

| Resultado | Significado |
|---|---|
| Taxa positiva | A água está subindo. |
| Taxa negativa | A água está descendo. |
| Taxa próxima de zero | O nível está relativamente estável. |

### 6.2. Classificação de risco

O sistema utiliza condições para classificar o estado do ponto monitorado:

| Estado | Condição |
|---|---|
| NORMAL | Nenhuma condição de atenção ou criticidade foi identificada. |
| ATENCAO | Nível igual ou superior a 60 cm e taxa de subida positiva. |
| CRITICO | Nível igual ou superior a 100 cm. |

Os valores utilizados são parâmetros demonstrativos do projeto, não limites oficiais de segurança.

### 6.3. Estimativa de tempo até o limite

Quando a água está subindo, o sistema também estima quanto tempo falta para atingir o limite crítico.

A fórmula utilizada é:

\[
t = \frac{H_{\text{limite}}-H_{\text{atual}}}{H'(t)}
\]

A estimativa só é realizada quando a taxa de variação é positiva e o nível atual ainda está abaixo do limite.

Exemplo:

- Nível atual: 80 cm.
- Limite crítico: 100 cm.
- Taxa de subida: 3 cm/s.

\[
t = \frac{100-80}{3} \approx 6,67 \text{ segundos}
\]

Essa previsão considera que a taxa de subida permanecerá constante, portanto representa uma estimativa simplificada, não uma garantia do comportamento futuro da água.

## 7. Integração com o Supabase

O Supabase é utilizado como serviço de armazenamento em nuvem e disponibilização dos dados.

Ele utiliza PostgreSQL como banco de dados e oferece uma API REST gerada automaticamente, permitindo que aplicações externas consultem os registros armazenados.

### 7.1. Funcionamento da integração

Depois de receber e processar uma mensagem MQTT, o Python envia os resultados para a tabela `leituras` do Supabase.

Cada leitura recebida gera um novo registro no banco de dados.

O Supabase armazena as informações e disponibiliza os dados por meio de sua API REST.

Dessa forma, o Dashboard React não precisa se conectar diretamente ao broker MQTT nem executar os cálculos realizados pelo Python.

Ele apenas consulta os dados já processados.

### 7.2. Estrutura da tabela

A tabela utilizada pelo projeto deve possuir os seguintes campos:

| Campo | Tipo sugerido | Descrição |
|---|---|---|
| `id` | bigint | Identificador do registro. |
| `ponto_id` | text | Identificação do ponto monitorado. |
| `timestamp` | timestamptz | Horário de inserção do registro. |
| `distancia_cm` | float8 | Distância medida pelo sensor. |
| `nivel_agua_cm` | float8 | Nível calculado da água. |
| `taxa_cm_por_s` | float8 | Taxa de variação do nível. |
| `estado` | text | Classificação do risco. |

A coluna `timestamp` pode ser configurada com o valor padrão `NOW()` no PostgreSQL.

Assim, o Supabase registra automaticamente o horário de inserção, sem exigir que o Python envie esse campo.

### 7.3. Acesso pelo React

O Dashboard pode utilizar a biblioteca oficial `@supabase/supabase-js` para consultar os dados.

Exemplo:

```javascript
const { data, error } = await supabase
  .from("leituras")
  .select("*")
  .order("timestamp", { ascending: false })
  .limit(20);
```

Essa consulta recupera as 20 leituras mais recentes.

O React pode utilizar essas informações para atualizar os indicadores, gráficos e alertas do Dashboard.

**Segurança:** a tabela deve possuir RLS (Row Level Security) habilitado e políticas adequadas para permitir somente as operações necessárias. A chave secreta utilizada pelo Python nunca deve ser incluída no código do React. Para o frontend, deve ser utilizada uma chave pública apropriada, com as permissões devidamente configuradas.

## 8. Bibliotecas utilizadas

### 8.1. Bibliotecas Python

| Biblioteca | Utilização |
|---|---|
| `json` | Interpretação das mensagens JSON recebidas pelo MQTT. |
| `os` | Acesso às variáveis de ambiente utilizadas nas configurações. |
| `paho-mqtt` | Comunicação com o broker MQTT, inscrição em tópicos e recebimento de mensagens. |
| `supabase` | Conexão com o Supabase e inserção dos dados na tabela `leituras`. |
| `python-dotenv` | Carregamento das configurações armazenadas no arquivo `.env`. |
| `datetime` | Conversão dos timestamps e cálculo dos intervalos de tempo entre as medições. |

### 8.2. Bibliotecas e tecnologias complementares

| Tecnologia | Utilização |
|---|---|
| ESP32 | Microcontrolador responsável pela leitura do sensor. |
| HC-SR04 | Sensor ultrassônico utilizado para medir a distância até a superfície da água. |
| Wokwi | Ambiente de simulação do ESP32 e dos componentes eletrônicos. |
| PubSubClient | Biblioteca C++ utilizada pelo ESP32 para comunicação MQTT. |
| Supabase | Banco de dados PostgreSQL e API REST. |
| React | Desenvolvimento da interface do Dashboard. |
| `@supabase/supabase-js` | Integração do Dashboard React com o Supabase. |

## 9. Estrutura de arquivos

Uma organização sugerida para os arquivos do backend é:

```text
HighWater/
│
├── backend/
│   ├── receptor.py
│   ├── .env
│   └── requirements.txt
│
├── firmware/
│   ├── sketch.ino
│   └── diagram.json
│
└── README.md
```

O Dashboard React pode permanecer em um repositório ou diretório separado, desenvolvido pelo integrante responsável pela interface.

### Arquivos necessários

**`receptor.py`**

Contém o código Python responsável por:

- Conectar ao broker MQTT.
- Receber as mensagens publicadas pelo ESP32.
- Calcular a taxa de variação do nível da água.
- Classificar o estado do ponto monitorado.
- Estimar o tempo até o limite crítico.
- Inserir os dados no Supabase.

**`.env`**

Armazena as credenciais de acesso ao Supabase.

Exemplo:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SECRET_KEY=sua_chave_secreta
```

Substitua os valores pelas credenciais reais do projeto.

Esse arquivo não deve ser enviado ao GitHub nem compartilhado publicamente.

**`requirements.txt`**

Lista as dependências Python necessárias para executar o backend.

Conteúdo:

```text
paho-mqtt
supabase
python-dotenv
```

**`sketch.ino`**

Contém o firmware C++ executado pelo ESP32 no Wokwi, incluindo:

- Configuração do Wi-Fi.
- Configuração do broker MQTT.
- Leitura do sensor HC-SR04.
- Cálculo do nível da água.
- Publicação das informações em JSON.

**`diagram.json`**

Arquivo utilizado pelo Wokwi para representar a montagem virtual dos componentes e suas conexões.

## 10. Instalação e configuração

### 10.1. Pré-requisitos

Antes de executar o projeto, é necessário possuir:

- Python instalado.
- Pip instalado.
- Conta no Supabase.
- Projeto criado no Supabase.
- Simulação do ESP32 configurada no Wokwi.
- Acesso ao broker MQTT utilizado pelo projeto.

### 10.2. Preparação do ambiente Python

Abra o terminal na pasta `backend` e crie um ambiente virtual:

```bash
python -m venv venv
```

Ative o ambiente virtual.

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### 10.3. Configuração do Supabase

1. Acesse o [Supabase](https://supabase.com/).
2. Crie um projeto.
3. Abra o SQL Editor.
4. Crie a tabela `leituras` utilizando a estrutura descrita anteriormente.
5. Configure o valor padrão `NOW()` na coluna `timestamp`.
6. Habilite RLS e configure as políticas de acesso.
7. Acesse as configurações de API do projeto.
8. Copie a URL do projeto e a chave secreta apropriada para o backend.
9. Preencha o arquivo `.env` com essas informações.

### 10.4. Configuração do Wokwi

1. Abra o projeto no Wokwi.
2. Verifique as conexões do ESP32 com o sensor HC-SR04.
3. Confira as configurações de Wi-Fi e broker MQTT no firmware.
4. Verifique se o tópico de publicação é `highwater/ponto01/leituras`.
5. Inicie a simulação.

O ESP32 deverá começar a publicar as medições periodicamente.

## 11. Como executar o projeto

A execução deve seguir esta ordem:

### Etapa 1 — Iniciar a simulação

Abra o projeto no Wokwi e inicie a simulação do ESP32.

O dispositivo deverá conectar-se à rede Wi-Fi simulada e ao broker MQTT.

### Etapa 2 — Iniciar o backend Python

No terminal, dentro da pasta `backend`, execute:

```bash
python receptor.py
```

O programa deverá exibir:

```text
Aguardando mensagens MQTT...
```

Após estabelecer a conexão com o broker:

```text
Conectado ao broker MQTT!
```

Quando uma nova leitura for recebida, serão exibidos os dados do sensor, a taxa de variação, o estado do ponto e, quando aplicável, o tempo estimado até o limite crítico.

Os resultados também serão enviados ao Supabase.

### Etapa 3 — Verificar o Supabase

Acesse o painel do projeto Supabase e abra a tabela `leituras`.

Cada nova mensagem processada pelo Python deverá gerar um registro.

Verifique se os campos estão sendo preenchidos corretamente.

### Etapa 4 — Iniciar ou acessar o Dashboard React

O integrante responsável pelo frontend deverá configurar a conexão com o Supabase utilizando a URL do projeto e a chave pública apropriada.

Depois, poderá executar o Dashboard normalmente.

Os dados armazenados no Supabase estarão disponíveis para consulta pela internet, permitindo que diferentes integrantes acessem as mesmas informações sem precisar executar o backend em seus computadores.

## 12. Observações importantes

- O computador responsável pelo backend precisa permanecer ligado enquanto o receptor Python estiver recebendo as mensagens MQTT.
- O Wokwi precisa permanecer executando para continuar produzindo novas leituras.
- O broker MQTT utilizado deve estar acessível e disponível.
- O Supabase mantém os dados armazenados mesmo depois que o Python é encerrado.
- O Dashboard pode consultar os registros armazenados independentemente de o Wokwi estar executando naquele momento.
- A API REST do Supabase permite consultar o histórico de leituras, mas não substitui o processamento realizado pelo Python.
- A estimativa de tempo até o limite é uma previsão simplificada baseada na taxa de variação atual.
- Os parâmetros de atenção e criticidade são valores demonstrativos e não devem ser utilizados como referência oficial para situações reais de emergência.

## 13. Resultado esperado

Ao executar todos os componentes, o HighWater deverá ser capaz de:

1. Simular medições de nível de água por meio do ESP32 e do HC-SR04.
2. Transmitir as leituras utilizando MQTT.
3. Receber e processar as informações com Python.
4. Calcular a taxa de variação do nível da água.
5. Classificar o estado do ponto monitorado.
6. Estimar o tempo até atingir o limite crítico, quando aplicável.
7. Armazenar os resultados no Supabase.
8. Disponibilizar os registros para consulta pelo Dashboard React.

Dessa maneira, o projeto demonstra uma integração entre IoT, comunicação MQTT, processamento de dados, cálculo diferencial, armazenamento em nuvem e desenvolvimento web.