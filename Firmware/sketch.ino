
#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>

// SENSORES

const int Trig = 25;
const int Echo = 26;

// CONFIGURACOES

const float ALTURA_REFERENCIA = 150.0;
const unsigned long INTERVALO_LEITURA = 3000;

// WI-FI

const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT

const char* mqtt_server = "3.93.68.31";
const int mqtt_port = 1883;

const char* topico_leituras = "highwater/ponto01/leituras";
const char* topico_comandos = "highwater/ponto01/comandos";

WiFiClient espClient;
PubSubClient client(espClient);

// CONTROLE DE TEMPO

unsigned long ultimaLeitura = 0;

// CONEXAO WI-FI

void conectarWiFi()
{
    Serial.print("Conectando ao Wi-Fi ");

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("Wi-Fi conectado!");
    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());
}

// CALLBACK MQTT

void callback(char* topic, byte* payload, unsigned int length)
{
    Serial.print("Mensagem recebida em ");
    Serial.println(topic);

    // Por enquanto, apenas exibimos os comandos recebidos.
}

// CONEXAO MQTT

void reconnect()
{
    while (!client.connected())
    {
        Serial.print("Conectando ao MQTT...");

        char clientId[40];

        snprintf(
            clientId,
            sizeof(clientId),
            "ESP32_HighWater_%04X",
            (unsigned int)(ESP.getEfuseMac() & 0xFFFF)
        );

        if (client.connect(clientId))
        {
            Serial.println(" conectado!");

            if (client.subscribe(topico_comandos))
            {
                Serial.print("Inscrito no topico: ");
                Serial.println(topico_comandos);
            }
        }
        else
        {
            Serial.print("Falha. Estado MQTT: ");
            Serial.println(client.state());

            delay(3000);
        }
    }
}

// LEITURA DO SENSOR

float medirDistancia()
{
    digitalWrite(Trig, LOW);
    delayMicroseconds(2);

    digitalWrite(Trig, HIGH);
    delayMicroseconds(10);

    digitalWrite(Trig, LOW);

    unsigned long duracao = pulseIn(Echo, HIGH, 30000);

    if (duracao == 0)
    {
        return -1;
    }

    float distancia = (duracao * 0.0343) / 2.0;

    return distancia;
}

// PUBLICACAO MQTT

void publicarLeitura(float distancia, float nivel)
{
    struct tm timeinfo;

    if (!getLocalTime(&timeinfo))
    {
        Serial.println("Aguardando sincronizacao do horario...");
        return;
    }

    char timestamp[30];

    strftime(
        timestamp,
        sizeof(timestamp),
        "%Y-%m-%dT%H:%M:%SZ",
        &timeinfo
    );

    char mensagem[200];

    snprintf(
        mensagem,
        sizeof(mensagem),
        "{\"ponto_id\":\"ponto01\","
        "\"timestamp\":\"%s\","
        "\"distancia_cm\":%.2f,"
        "\"nivel_agua_cm\":%.2f}",
        timestamp,
        distancia,
        nivel
    );

    if (client.publish(topico_leituras, mensagem))
    {
        Serial.println("Leitura publicada:");
        Serial.println(mensagem);
    }
    else
    {
        Serial.println("Falha ao publicar leitura.");
    }
}

// SETUP

void setup()
{
    Serial.begin(115200);

    pinMode(Trig, OUTPUT);
    pinMode(Echo, INPUT);

    conectarWiFi();

    // Sincroniza o horario usando NTP (UTC)
    configTime(0, 0, "pool.ntp.org", "time.google.com");

    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);
}

// LOOP

void loop()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        conectarWiFi();
    }

    if (!client.connected())
    {
        reconnect();
    }

    client.loop();

    unsigned long agora = millis();

    if (agora - ultimaLeitura >= INTERVALO_LEITURA)
    {
        ultimaLeitura = agora;

        float distancia = medirDistancia();

        if (distancia < 0 || distancia > ALTURA_REFERENCIA)
        {
            Serial.println("Leitura invalida do sensor.");
            return;
        }

        float nivel = ALTURA_REFERENCIA - distancia;

        Serial.print("Distancia: ");
        Serial.print(distancia);
        Serial.println(" cm");

        Serial.print("Nivel da agua: ");
        Serial.print(nivel);
        Serial.println(" cm");

        publicarLeitura(distancia, nivel);
    }
}
