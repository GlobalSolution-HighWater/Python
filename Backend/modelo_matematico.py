"""
Modelo matemático do projeto High Water: limite, derivada e integral.

Este arquivo NÃO altera o receptor MQTT nem o analise_matematica.py.
Ele apenas reutiliza a função buscar_leituras() do analise_matematica.py
para ler a tabela `leituras` do Supabase e, a partir dessas medições:

  Questão 01 - ajusta a função H(t) aos dados e calcula limites;
  Questão 02 - deriva H(t), estuda o sinal da derivada, os pontos críticos
               (máximo) e os pontos de inflexão;
  Questão 03 - integra H(t) (indefinida e definida), calcula a área sob a
               curva, a exposição acima dos níveis de alerta e o volume.

Variáveis:
    t     : tempo desde a primeira leitura analisada [s]
    H(t)  : nível da água acima do fundo do bueiro [cm]
    H'(t) : taxa de variação instantânea do nível [cm/s]

Função utilizada (gaussiana com nível-base):

    H(t) = B + A * exp( -(t - mu)^2 / (2 sigma^2) )

Um evento de cheia tem fase de subida, pico e fase de descida; a curva em
forma de sino (função gaussiana, estudada em Cálculo, p. ex. STEWART, J.
Cálculo, vol. 1 e 2) reproduz esse formato com poucos parâmetros:
    B     : nível-base do bueiro [cm]
    A     : altura do pico acima da base [cm]
    mu    : instante do pico [s]
    sigma : largura do evento [s]
Os parâmetros NÃO são inventados: são estimados pelo método dos mínimos
quadrados a partir das medições reais gravadas no Supabase, com a restrição
física B >= 0 (o nível medido a partir do fundo não pode ser negativo).
Para mu e sigma fixos o modelo é linear em B e A (regressão linear simples); mu e
sigma são buscados em uma grade refinada várias vezes (separação de
variáveis, GOLUB; PEREYRA, SIAM J. Numer. Anal. 10(2), 1973).

Dependências: apenas numpy e matplotlib (as mesmas do analise_matematica.py).
    pip install numpy matplotlib

Uso:
    python modelo_matematico.py
    python modelo_matematico.py --inicio 2026-11-18T17:05 --fim 2026-11-18T17:10
    python modelo_matematico.py --csv leituras.csv      (colunas: timestamp,nivel_agua_cm)
    python modelo_matematico.py --sem-janela            (só salva os arquivos)

Saídas (pasta "saidas"): 5 gráficos PNG e resultados.json.
"""

import argparse
import csv
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone

import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# PARÂMETROS DO PROBLEMA
# ============================================================

# Mesmos valores utilizados no firmware e no receptor_mqtt.py.
ALTURA_REFERENCIA = 150.0   # cm - distância sensor -> fundo do bueiro
NIVEL_ATENCAO = 60.0        # cm - limite demonstrativo de ATENÇÃO
NIVEL_CRITICO = 100.0       # cm - limite demonstrativo de CRÍTICO

# PREMISSA: diâmetro interno do bueiro, usado apenas para converter nível
# em volume (V = área da seção x altura). Ajuste para o valor do seu projeto.
DIAMETRO_BUEIRO_CM = 100.0

PASTA_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saidas")
FUSO_PADRAO = timezone(timedelta(hours=-3))  # São Paulo


# ============================================================
# LEITURA E PREPARAÇÃO DOS DADOS
# ============================================================

def converter_timestamp(valor):
    """Converte timestamps ISO (com ou sem fuso) para datetime com fuso."""
    valor = valor.strip().replace(" ", "T")
    if valor.endswith("Z"):
        valor = valor[:-1] + "+00:00"
    # Normaliza a fração de segundos para 6 dígitos (compatível com Python < 3.11).
    valor = re.sub(
        r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), valor
    )
    instante = datetime.fromisoformat(valor)
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=FUSO_PADRAO)
    return instante


def carregar_leituras(caminho_csv):
    """Lê as medições do Supabase (padrão) ou de um CSV (opcional)."""
    if caminho_csv:
        with open(caminho_csv, newline="", encoding="utf-8") as arquivo:
            return list(csv.DictReader(arquivo))

    # Reutiliza a busca já existente, sem duplicar a conexão com o Supabase.
    from analise_matematica import buscar_leituras
    return buscar_leituras()


def preparar_dados(leituras, inicio, fim):
    itens = []
    for leitura in leituras:
        instante = converter_timestamp(leitura["timestamp"])
        itens.append((instante, float(leitura["nivel_agua_cm"])))
    itens.sort(key=lambda par: par[0])

    if inicio:
        limite = converter_timestamp(inicio)
        itens = [par for par in itens if par[0] >= limite]
    if fim:
        limite = converter_timestamp(fim)
        itens = [par for par in itens if par[0] <= limite]

    if len(itens) < 5:
        raise ValueError(
            "São necessárias pelo menos 5 leituras no intervalo escolhido "
            "para ajustar o modelo (ele possui 4 parâmetros)."
        )

    instantes = [par[0] for par in itens]
    t = np.array([(i - instantes[0]).total_seconds() for i in instantes])
    h = np.array([par[1] for par in itens])

    # Remove instantes repetidos (não existe taxa entre medições simultâneas).
    validos = np.concatenate(([True], np.diff(t) > 0))
    return t[validos], h[validos], instantes[0]


# ============================================================
# QUESTÃO 01 - FUNÇÃO H(t) E LIMITES
# ============================================================

def gaussiana(t, B, A, mu, sigma):
    """H(t) = B + A exp(-(t - mu)^2 / (2 sigma^2))."""
    return B + A * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))


def _melhor_ajuste_linear(t, h, mu_grade, sigma):
    """
    Para sigma fixo e vários mu, resolve B e A por regressão linear
    (H = B + A*s, com s = exp(-(t-mu)^2/(2 sigma^2))) e devolve o erro quadrático.
    """
    s = np.exp(-((t[None, :] - mu_grade[:, None]) ** 2) / (2 * sigma ** 2))
    s_med = s.mean(axis=1)
    h_med = h.mean()
    var_s = ((s - s_med[:, None]) ** 2).sum(axis=1)
    cov = ((s - s_med[:, None]) * (h - h_med)).sum(axis=1)
    A = np.divide(cov, var_s, out=np.zeros_like(cov), where=var_s > 1e-12)
    B = h_med - A * s_med
    # Restrição física: o nível-base não pode ser negativo (B >= 0).
    # Quando a regressão livre dá B < 0, fixa-se B = 0 e A é refeito
    # pelos mínimos quadrados da reta que passa pela origem.
    negativo = B < 0
    if np.any(negativo):
        A_zero = np.divide((s * h).sum(axis=1), (s ** 2).sum(axis=1))
        A = np.where(negativo, A_zero, A)
        B = np.where(negativo, 0.0, B)
    sse = ((h - (B[:, None] + A[:, None] * s)) ** 2).sum(axis=1)
    return sse, B, A


def ajustar_modelo(t, h):
    """Estima B, A, mu, sigma por mínimos quadrados (grade refinada)."""
    if np.ptp(h) < 1e-6:
        raise ValueError("O nível não variou; não há curva para ajustar.")

    duracao = float(t[-1] - t[0])
    sig_min, sig_max = duracao / 50.0, duracao * 2.0
    mu_min, mu_max = t[0] - 0.25 * duracao, t[-1] + 0.25 * duracao
    melhor = None

    for _ in range(6):  # a cada rodada, a grade fica menor em torno do melhor ponto
        mu_grade = np.linspace(mu_min, mu_max, 241)
        for sigma in np.geomspace(sig_min, sig_max, 121):
            sse, B, A = _melhor_ajuste_linear(t, h, mu_grade, sigma)
            i = int(np.argmin(sse))
            if melhor is None or sse[i] < melhor[0]:
                melhor = (float(sse[i]), float(B[i]), float(A[i]), float(mu_grade[i]), float(sigma))
        _, _, _, mu_b, sig_b = melhor
        sig_min, sig_max = sig_b / 1.5, sig_b * 1.5
        passo = (mu_max - mu_min) / 240
        mu_min, mu_max = mu_b - 4 * passo, mu_b + 4 * passo

    sse, B, A, mu, sigma = melhor
    residuos = h - gaussiana(t, B, A, mu, sigma)
    sst = float(np.sum((h - h.mean()) ** 2))
    r2 = 1 - sse / sst if sst > 0 else float("nan")
    rmse = float(np.sqrt(sse / len(t)))
    return (B, A, mu, sigma), r2, rmse, residuos


def analisar_limites(B, A, mu, sigma):
    """
    Limites de H(t) (deduzidos analiticamente) e conferência numérica.

    t -> +inf e t -> -inf: exp(-(t-mu)^2/(2 sigma^2)) -> 0  =>  H -> B
    t -> mu              : H -> H(mu) = B + A   (continuidade)
    h -> 0               : [H(mu+h) - H(mu)]/h -> H'(mu) = 0 (tangente horizontal no pico)
    """
    tabela = []
    for passo in (10.0, 1.0, 0.1, 0.01, 0.001):
        quociente = (gaussiana(mu + passo, B, A, mu, sigma) - gaussiana(mu, B, A, mu, sigma)) / passo
        tabela.append({"h": passo, "quociente": float(quociente)})

    return {
        "limite_mais_infinito": float(B),
        "limite_menos_infinito": float(B),
        "limite_em_mu": float(B + A),
        "conferencia_t_grande": float(gaussiana(mu + 1e4, B, A, mu, sigma)),
        "conferencia_t_muito_negativo": float(gaussiana(mu - 1e4, B, A, mu, sigma)),
        "limite_derivada_t0": 0.0,
        "tabela_quociente": tabela,
    }


# ============================================================
# QUESTÃO 02 - DERIVADA
# ============================================================

def instantes_nivel(nivel, B, A, mu, sigma):
    """
    Resolve H(t) = nivel. Com r = (nivel - B)/A, exp(-(t-mu)^2/(2 sigma^2)) = r
    => t = mu -/+ sigma sqrt(-2 ln r), com 0 < r <= 1.
    Retorna (instante de subida, instante de descida) ou (None, None).
    """
    r = (nivel - B) / A
    if not (0 < r <= 1):
        return None, None
    d = sigma * math.sqrt(-2 * math.log(r))
    return float(mu - d), float(mu + d)


def analisar_derivada(t, h, B, A, mu, sigma):
    """
    Com s(t) = exp(-(t-mu)^2/(2 sigma^2)), pela regra da cadeia:
        H'(t)  = -A (t - mu) s / sigma^2
        H''(t) =  A s / sigma^2 * [ (t - mu)^2 / sigma^2 - 1 ]
    s > 0 sempre, então H'(t) = 0 apenas em t = mu (único ponto crítico);
    H''(mu) = -A / sigma^2 < 0 (se A > 0): máximo local.
    H''(t) = 0 em t = mu -/+ sigma (pontos de inflexão, onde |H'| é máxima).
    """
    def f_derivada(x):
        x = np.asarray(x, dtype=float)
        return -A * (x - mu) / sigma ** 2 * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))

    taxa_numerica = np.gradient(h, t)            # diferenças finitas
    rmse_taxa = float(np.sqrt(np.mean((f_derivada(t) - taxa_numerica) ** 2)))
    fator = math.exp(-0.5)

    resultado = {
        "expr_derivada": "H'(t) = -A (t - mu) exp(-(t-mu)^2/(2 sigma^2)) / sigma^2",
        "expr_segunda_derivada": "H''(t) = A exp(-(t-mu)^2/(2 sigma^2)) [ (t-mu)^2/sigma^2 - 1 ] / sigma^2",
        "pontos_criticos": [f"t = mu = {mu:.2f} s"],
        "classificacao_ponto_critico": "máximo local" if A > 0 else "mínimo local",
        "t_pico_s": float(mu),
        "nivel_pico_cm": float(B + A),
        "segunda_derivada_no_pico": float(-A / sigma ** 2),
        "inflexao_s": [float(mu - sigma), float(mu + sigma)],
        "nivel_inflexao_cm": float(B + A * fator),
        "taxa_max_subida_cm_s": float(A * fator / sigma),
        "taxa_max_descida_cm_s": float(-A * fator / sigma),
        "taxa_inicial_cm_s": float(f_derivada(t[0])),
        "taxa_final_cm_s": float(f_derivada(t[-1])),
        "rmse_taxa_modelo_vs_numerica": rmse_taxa,
    }
    for nome, nivel in (("atencao", NIVEL_ATENCAO), ("critico", NIVEL_CRITICO)):
        sobe, desce = instantes_nivel(nivel, B, A, mu, sigma)
        resultado[f"t_{nome}_sobe_s"] = sobe
        resultado[f"t_{nome}_desce_s"] = desce
        resultado[f"tempo_acima_{nome}_s"] = (desce - sobe) if sobe is not None else None
        resultado[f"taxa_{nome}_sobe_cm_s"] = float(f_derivada(sobe)) if sobe is not None else None
    return resultado, f_derivada, taxa_numerica


# ============================================================
# QUESTÃO 03 - INTEGRAL
# ============================================================

_erf = np.vectorize(math.erf)


def primitiva(t, B, A, mu, sigma):
    """
    F(t) = B t + A sigma sqrt(pi/2) erf((t - mu) / (sigma sqrt(2))).
    Dedução: com z = (t - mu)/(sigma sqrt 2), dt = sigma sqrt2 dz e
    erf(z) = (2/sqrt(pi)) * integral de e^(-z^2) dz, logo
    integral de A e^(-(t-mu)^2/(2 sigma^2)) dt = A sigma sqrt(pi/2) erf(z).
    """
    z = (np.asarray(t, dtype=float) - mu) / (sigma * math.sqrt(2))
    return B * np.asarray(t, dtype=float) + A * sigma * math.sqrt(math.pi / 2) * _erf(z)


def trapezios(x, y):
    """Regra dos trapézios (integração numérica)."""
    return float(np.sum((y[:-1] + y[1:]) * 0.5 * np.diff(x)))


def analisar_integral(t, h, B, A, mu, sigma, f_derivada):
    T = float(t[-1])

    # Conferência de F'(t) = H(t) por diferença central.
    x = np.linspace(0, T, 400)
    passo = 1e-4
    dF = (primitiva(x + passo, B, A, mu, sigma) - primitiva(x - passo, B, A, mu, sigma)) / (2 * passo)
    primitiva_ok = bool(np.max(np.abs(dF - gaussiana(x, B, A, mu, sigma))) < 1e-4)

    integral_analitica = float(primitiva(T, B, A, mu, sigma) - primitiva(0.0, B, A, mu, sigma))
    fino = np.linspace(0, T, 20001)
    H_fino = gaussiana(fino, B, A, mu, sigma)
    integral_modelo_num = trapezios(fino, H_fino)
    integral_dados = trapezios(t, h)
    nivel_medio = integral_analitica / T          # teorema do valor médio

    # Exposição acima dos níveis de alerta (não depende da geometria do bueiro).
    exp_atencao = trapezios(fino, np.maximum(H_fino - NIVEL_ATENCAO, 0.0))
    exp_critico = trapezios(fino, np.maximum(H_fino - NIVEL_CRITICO, 0.0))

    # Volume: Q(t) = S H'(t); entrada = integral de Q^+, saída = integral de Q^-.
    raio = DIAMETRO_BUEIRO_CM / 2.0
    secao_cm2 = float(np.pi * raio ** 2)
    Q = secao_cm2 * f_derivada(fino) / 1000.0     # L/s
    v_entrada = trapezios(fino, np.maximum(Q, 0.0))
    v_saida = trapezios(fino, np.maximum(-Q, 0.0))
    delta_h = float(gaussiana(T, B, A, mu, sigma) - gaussiana(0.0, B, A, mu, sigma))

    return {
        "primitiva_verificada": primitiva_ok,
        "T_s": T,
        "integral_analitica_cm_s": integral_analitica,
        "integral_numerica_modelo_cm_s": float(integral_modelo_num),
        "integral_trapezios_dados_cm_s": integral_dados,
        "diferenca_modelo_dados_pct": float(
            100 * (integral_analitica - integral_dados) / integral_dados
        ),
        "nivel_medio_cm": float(nivel_medio),
        "exposicao_acima_atencao_cm_s": float(exp_atencao),
        "exposicao_acima_critico_cm_s": float(exp_critico),
        "diametro_bueiro_cm": DIAMETRO_BUEIRO_CM,
        "secao_cm2": secao_cm2,
        "volume_entrada_litros": float(v_entrada),
        "volume_saida_litros": float(v_saida),
        "volume_liquido_litros": float(secao_cm2 * delta_h / 1000.0),
        "delta_h_total_cm": delta_h,
        "vazao_enchimento_max_l_s": float(secao_cm2 * A * math.exp(-0.5) / sigma / 1000.0),
    }


# ============================================================
# GRÁFICOS
# ============================================================

def gerar_graficos(t, h, parametros, taxa_numerica, f_derivada, residuos, resumo):
    B, A, mu, sigma = parametros
    T = float(t[-1])
    t_fino = np.linspace(0, T, 600)
    H_fino = gaussiana(t_fino, B, A, mu, sigma)
    pasta = lambda nome: os.path.join(PASTA_SAIDA, nome)

    # 1) Dados e modelo ajustado --------------------------------------
    plt.figure(figsize=(10, 5))
    plt.plot(t, h, "o", label="Medições (Supabase)")
    plt.plot(t_fino, H_fino, label=f"Modelo ajustado (R² = {resumo['r2']:.4f})")
    plt.axhline(B, linestyle="--", color="gray",
                label=f"Limite de H(t) quando t → ±∞: {B:.1f} cm")
    plt.plot([mu], [B + A], "r*", markersize=14,
             label=f"Pico: {B + A:.1f} cm em t = {mu:.1f} s")
    plt.axhline(NIVEL_ATENCAO, linestyle=":", color="orange", label="Atenção (60 cm)")
    plt.axhline(NIVEL_CRITICO, linestyle=":", color="red", label="Crítico (100 cm)")
    plt.title("Nível da água no bueiro: medições e função ajustada")
    plt.xlabel("Tempo decorrido (s)")
    plt.ylabel("Nível da água H(t) (cm)")
    plt.grid(True)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(pasta("01_modelo.png"), dpi=150)

    # 2) Derivada ------------------------------------------------------
    d = f_derivada(t_fino)
    plt.figure(figsize=(10, 5))
    plt.plot(t, taxa_numerica, "o", label="Diferenças finitas (dados)")
    plt.plot(t_fino, d, label="Derivada analítica H'(t)")
    plt.axhline(0, linewidth=1, color="black")
    plt.axvline(mu, linestyle="--", color="gray", label=f"Ponto crítico (pico): t = {mu:.1f} s")
    plt.plot([mu - sigma, mu + sigma],
             [A * math.exp(-0.5) / sigma, -A * math.exp(-0.5) / sigma], "r*", markersize=12,
             label="Pontos de inflexão de H(t) (extremos de H')")
    plt.title("Taxa de variação instantânea do nível da água")
    plt.xlabel("Tempo decorrido (s)")
    plt.ylabel("Taxa de variação H'(t) (cm/s)")
    plt.grid(True)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(pasta("02_derivada.png"), dpi=150)

    # 3) Integral: área e integral acumulada ---------------------------
    fig, eixos = plt.subplots(1, 2, figsize=(12, 5))
    eixos[0].plot(t_fino, H_fino, color="C0")
    eixos[0].fill_between(
        t_fino, 0, H_fino, alpha=0.3,
        label=f"Área = {resumo['integral_analitica_cm_s']:.1f} cm·s")
    eixos[0].set_title("Área sob a curva H(t) em [0, T]")
    eixos[0].set_xlabel("Tempo decorrido (s)")
    eixos[0].set_ylabel("Nível da água H(t) (cm)")
    eixos[0].grid(True)
    eixos[0].legend()

    acumulada = primitiva(t_fino, B, A, mu, sigma) - primitiva(0.0, B, A, mu, sigma)
    eixos[1].plot(t_fino, acumulada, color="C2")
    eixos[1].set_title("Integral acumulada de H(t)")
    eixos[1].set_xlabel("Tempo decorrido (s)")
    eixos[1].set_ylabel("Integral acumulada (cm·s)")
    eixos[1].grid(True)
    fig.tight_layout()
    fig.savefig(pasta("03_integral.png"), dpi=150)

    # 4) Volume acumulado e vazão ---------------------------------------
    S = resumo["secao_cm2"]
    volume = S * (H_fino - gaussiana(0.0, B, A, mu, sigma)) / 1000.0
    vazao = S * d / 1000.0
    fig, eixos = plt.subplots(1, 2, figsize=(12, 5))
    eixos[0].plot(t_fino, volume, color="C3")
    eixos[0].set_title("Volume de água acumulado V(t) (premissa de diâmetro)")
    eixos[0].set_xlabel("Tempo decorrido (s)")
    eixos[0].set_ylabel("Volume acumulado (L)")
    eixos[0].grid(True)
    eixos[1].plot(t_fino, vazao, color="C1")
    eixos[1].axhline(0, color="black", linewidth=1)
    eixos[1].set_title("Vazão equivalente Q(t) (+ enche, − esvazia)")
    eixos[1].set_xlabel("Tempo decorrido (s)")
    eixos[1].set_ylabel("Vazão (L/s)")
    eixos[1].grid(True)
    fig.tight_layout()
    fig.savefig(pasta("04_volume_vazao.png"), dpi=150)

    # 5) Resíduos ---------------------------------------------------------
    plt.figure(figsize=(10, 4))
    plt.axhline(0, color="black", linewidth=1)
    plt.plot(t, residuos, "o-")
    plt.title("Resíduos do ajuste (medido − modelo)")
    plt.xlabel("Tempo decorrido (s)")
    plt.ylabel("Resíduo (cm)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(pasta("05_residuos.png"), dpi=150)


# ============================================================
# EXECUÇÃO
# ============================================================

def ler_argumentos():
    parser = argparse.ArgumentParser(description="Modelo matemático High Water")
    parser.add_argument("--inicio", help="Só usa leituras a partir deste instante (ISO).")
    parser.add_argument("--fim", help="Só usa leituras até este instante (ISO).")
    parser.add_argument("--csv", help="Usa um CSV (timestamp,nivel_agua_cm) em vez do Supabase.")
    parser.add_argument("--sem-janela", action="store_true",
                        help="Salva os gráficos sem abrir janelas.")
    return parser.parse_args()


def fmt(valor, unidade=""):
    return "não ocorre no modelo" if valor is None else f"{valor:.1f}{unidade}"


def main():
    args = ler_argumentos()
    if args.sem_janela:
        plt.switch_backend("Agg")
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    print("Carregando medições...")
    leituras = carregar_leituras(args.csv)
    t, h, instante_inicial = preparar_dados(leituras, args.inicio, args.fim)

    # ---------------- Questão 01 ----------------
    (B, A, mu, sigma), r2, rmse, residuos = ajustar_modelo(t, h)
    limites = analisar_limites(B, A, mu, sigma)

    print("\n=== QUESTÃO 01 - MODELO E LIMITES ===")
    print(f"Medições usadas: {len(t)} | duração: {t[-1]:.1f} s")
    print("H(t) = B + A exp(-(t - mu)^2 / (2 sigma^2))")
    print(f"  B     = {B:.3f} cm  (nível-base)")
    print(f"  A     = {A:.3f} cm  (altura do pico acima da base)")
    print(f"  mu    = {mu:.2f} s   (instante do pico)")
    print(f"  sigma = {sigma:.2f} s   (largura do evento)")
    print(f"Qualidade do ajuste: R² = {r2:.4f} | RMSE = {rmse:.3f} cm")
    if r2 < 0.9:
        print("ATENÇÃO: R² baixo. Escolha um trecho que contenha uma única "
              "subida e descida (use --inicio e --fim).")
    if A < 0:
        print("ATENÇÃO: A < 0 (o ajuste encontrou um vale, não um pico).")
    print(f"lim H(t), t -> ±inf = {limites['limite_mais_infinito']:.2f} cm")
    print(f"lim H(t), t -> mu   = {limites['limite_em_mu']:.2f} cm")
    print(f"lim (H(mu+h)-H(mu))/h, h -> 0 = {limites['limite_derivada_t0']:.1f} cm/s")

    # ---------------- Questão 02 ----------------
    derivada, f_derivada, taxa_numerica = analisar_derivada(t, h, B, A, mu, sigma)
    print("\n=== QUESTÃO 02 - DERIVADA ===")
    print(derivada["expr_derivada"])
    print(derivada["expr_segunda_derivada"])
    print(f"Ponto crítico: {derivada['pontos_criticos'][0]} -> {derivada['classificacao_ponto_critico']} "
          f"(H = {derivada['nivel_pico_cm']:.1f} cm, H'' = {derivada['segunda_derivada_no_pico']:.4f})")
    print(f"H crescente em t < {mu:.1f} s e decrescente em t > {mu:.1f} s")
    print(f"Inflexão em t = {derivada['inflexao_s'][0]:.1f} s e {derivada['inflexao_s'][1]:.1f} s "
          f"(nível {derivada['nivel_inflexao_cm']:.1f} cm)")
    print(f"Taxa máxima de subida: {derivada['taxa_max_subida_cm_s']:.3f} cm/s | "
          f"de descida: {derivada['taxa_max_descida_cm_s']:.3f} cm/s")
    for nome, rotulo in (("atencao", "60 cm"), ("critico", "100 cm")):
        print(f"H = {rotulo}: sobe em {fmt(derivada[f't_{nome}_sobe_s'], ' s')}, "
              f"desce em {fmt(derivada[f't_{nome}_desce_s'], ' s')}, "
              f"tempo acima: {fmt(derivada[f'tempo_acima_{nome}_s'], ' s')}")

    # ---------------- Questão 03 ----------------
    integral = analisar_integral(t, h, B, A, mu, sigma, f_derivada)
    print("\n=== QUESTÃO 03 - INTEGRAL ===")
    print("Primitiva F(t) = B t + A sigma sqrt(pi/2) erf((t-mu)/(sigma sqrt 2))  "
          f"(verificada: {integral['primitiva_verificada']})")
    print(f"Integral definida de 0 a {integral['T_s']:.1f} s: "
          f"{integral['integral_analitica_cm_s']:.2f} cm·s")
    print(f"  trapézios sobre o modelo: {integral['integral_numerica_modelo_cm_s']:.2f} cm·s")
    print(f"  trapézios sobre os dados: {integral['integral_trapezios_dados_cm_s']:.2f} cm·s "
          f"(diferença {integral['diferenca_modelo_dados_pct']:.2f}%)")
    print(f"Nível médio no período: {integral['nivel_medio_cm']:.2f} cm")
    print(f"Exposição acima de 60 cm: {integral['exposicao_acima_atencao_cm_s']:.1f} cm·s | "
          f"acima de 100 cm: {integral['exposicao_acima_critico_cm_s']:.1f} cm·s")
    print(f"Volume (premissa D = {DIAMETRO_BUEIRO_CM:.0f} cm): entrada {integral['volume_entrada_litros']:.1f} L, "
          f"saída {integral['volume_saida_litros']:.1f} L, líquido {integral['volume_liquido_litros']:.1f} L")

    # ---------------- Saídas ----------------
    resumo = {**integral, "r2": r2}
    gerar_graficos(t, h, (B, A, mu, sigma), taxa_numerica, f_derivada, residuos, resumo)

    resultados = {
        "dados": {
            "n_medicoes": int(len(t)),
            "duracao_s": float(t[-1]),
            "inicio_iso": instante_inicial.isoformat(),
            "intervalo_medio_s": float(np.mean(np.diff(t))),
            "nivel_minimo_cm": float(h.min()),
            "nivel_maximo_cm": float(h.max()),
            "altura_referencia_cm": ALTURA_REFERENCIA,
            "nivel_atencao_cm": NIVEL_ATENCAO,
            "nivel_critico_cm": NIVEL_CRITICO,
        },
        "modelo": {"B": B, "A": A, "mu": mu, "sigma": sigma, "r2": r2, "rmse_cm": rmse},
        "limites": limites,
        "derivada": derivada,
        "integral": integral,
        "pontos": {"t_s": [float(x) for x in t], "nivel_cm": [float(x) for x in h]},
    }
    with open(os.path.join(PASTA_SAIDA, "resultados.json"), "w", encoding="utf-8") as arq:
        json.dump(resultados, arq, ensure_ascii=False, indent=2)

    print(f"\nArquivos salvos em: {PASTA_SAIDA}")
    if not args.sem_janela:
        plt.show()


if __name__ == "__main__":
    main()