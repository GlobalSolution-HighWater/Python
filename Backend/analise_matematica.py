"""
Análise matemática dos dados do projeto High Water.

Este arquivo consulta as medições já armazenadas na tabela `leituras` do Supabase.
Ele não altera nem substitui o receptor MQTT.

Variáveis utilizadas:
- t: tempo decorrido desde a primeira leitura, em segundos.
- H(t): nível da água, em centímetros.
- dH/dt: taxa de variação aproximada do nível, em cm/s.
- Integral de H(t): área aproximada sob a curva nível x tempo, em cm.s.

Dependências adicionais:
    pip install numpy matplotlib

As bibliotecas supabase e python-dotenv já são utilizadas pelo receptor.
"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# CONFIGURAÇÃO E CONEXÃO COM O SUPABASE
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Não foi possível encontrar SUPABASE_URL e SUPABASE_SECRET_KEY. "
        "Verifique se o arquivo .env está na pasta Backend."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# BUSCA DAS MEDIÇÕES
# ============================================================

def buscar_leituras():
    """Busca todas as leituras da tabela, em ordem cronológica."""
    leituras = []
    inicio = 0
    tamanho_pagina = 1000

    while True:
        resposta = (
            supabase.table("leituras")
            .select("timestamp,nivel_agua_cm,distancia_cm,taxa_cm_por_s,estado")
            .order("timestamp")
            .range(inicio, inicio + tamanho_pagina - 1)
            .execute()
        )

        pagina = resposta.data or []
        leituras.extend(pagina)

        if len(pagina) < tamanho_pagina:
            break

        inicio += tamanho_pagina

    return leituras


def converter_timestamp(valor):
    """Converte o timestamp ISO do Supabase para datetime."""
    if valor.endswith("Z"):
        valor = valor[:-1] + "+00:00"
    return datetime.fromisoformat(valor)


# ============================================================
# PREPARAÇÃO DOS DADOS
# ============================================================

def preparar_dados(leituras):
    if len(leituras) < 2:
        raise ValueError(
            "São necessárias pelo menos duas leituras no Supabase "
            "para calcular a taxa de variação."
        )

    tempos = [converter_timestamp(item["timestamp"]) for item in leituras]
    niveis = [float(item["nivel_agua_cm"]) for item in leituras]

    # Converte os timestamps em segundos a partir da primeira medição.
    tempo_inicial = tempos[0]
    t = np.array(
        [(instante - tempo_inicial).total_seconds() for instante in tempos],
        dtype=float,
    )
    h = np.array(niveis, dtype=float)

    # Remove pontos com tempo repetido, pois não é possível calcular
    # uma taxa entre duas medições que tenham o mesmo instante.
    indices_validos = np.concatenate(([True], np.diff(t) > 0))
    t = t[indices_validos]
    h = h[indices_validos]

    if len(t) < 2:
        raise ValueError(
            "As leituras não possuem timestamps distintos suficientes "
            "para realizar a análise."
        )

    return t, h


# ============================================================
# CÁLCULOS NUMÉRICOS
# ============================================================

def calcular_derivada_numerica(t, h):
    """
    Aproxima dH/dt usando diferenças finitas.
    O resultado representa a variação do nível em cm por segundo.
    """
    return np.gradient(h, t)


def calcular_integral_numerica(t, h):
    """
    Aproxima a integral definida de H(t) pelo método dos trapézios.
    Unidade: cm.s (centímetro vezes segundo).
    """
    areas = (h[:-1] + h[1:]) * 0.5 * np.diff(t)
    integral_total = np.sum(areas)
    integral_acumulada = np.concatenate(([0.0], np.cumsum(areas)))
    return integral_total, integral_acumulada


# ============================================================
# GRÁFICOS
# ============================================================

def gerar_graficos(t, h, derivada, integral_acumulada):
    plt.figure(figsize=(10, 5))
    plt.plot(t, h, marker="o", label="Nível da água")
    plt.title("Nível da água ao longo do tempo")
    plt.xlabel("Tempo decorrido (s)")
    plt.ylabel("Nível da água (cm)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.figure(figsize=(10, 5))
    plt.plot(t, derivada, marker="o", label="Taxa de variação aproximada")
    plt.axhline(0, linewidth=1)
    plt.title("Taxa de variação do nível da água")
    plt.xlabel("Tempo decorrido (s)")
    plt.ylabel("Taxa de variação (cm/s)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.figure(figsize=(10, 5))
    plt.plot(t, integral_acumulada, marker="o", label="Integral acumulada")
    plt.title("Acúmulo da área sob a curva do nível da água")
    plt.xlabel("Tempo decorrido (s)")
    plt.ylabel("Integral acumulada (cm.s)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.show()


# ============================================================
# EXECUÇÃO
# ============================================================

def main():
    print("Buscando medições no Supabase...")
    leituras = buscar_leituras()

    if not leituras:
        print("A tabela 'leituras' ainda não possui medições.")
        return

    t, h = preparar_dados(leituras)
    derivada = calcular_derivada_numerica(t, h)
    integral_total, integral_acumulada = calcular_integral_numerica(t, h)

    print(f"\nQuantidade de medições analisadas: {len(t)}")
    print(f"Tempo total observado: {t[-1]:.2f} s")
    print(f"Menor nível registrado: {np.min(h):.2f} cm")
    print(f"Maior nível registrado: {np.max(h):.2f} cm")
    print(f"Integral aproximada no período: {integral_total:.2f} cm.s")

    print("\nTaxa de variação aproximada em cada instante:")
    for instante, taxa in zip(t, derivada):
        print(f"Tempo: {instante:8.2f} s | Taxa: {taxa:8.3f} cm/s")

    print(
        "\nObservação: estes cálculos são aproximações numéricas feitas "
        "diretamente sobre as medições. A construção e a derivação de uma "
        "função matemática ajustada aos dados serão uma etapa posterior."
    )

    gerar_graficos(t, h, derivada, integral_acumulada)


if __name__ == "__main__":
    main()
