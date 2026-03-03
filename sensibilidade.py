from main import MyProblem, MyOutput
import os
import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.termination import get_termination
from pymoo.optimize import minimize
from time import sleep
import pandas as pd


# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------- Definicao do parametros de otimização ----------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# Variações dos parametros:
variacao = np.array([0.6, 0.8, 1.2, 1.4])

# Parâmetros financeiros e operacionais
preco_diesel = 5.78
vetor_preco_diesel = [3.69, 5.78, 7.46]                                                                         # R$/litro
rendimento_diesel = 3.6                                                                                         # kWh/litro

# Estimativa do preço da eletronica de potencia
total_elepot = 2000                                                                                             # Potencia total que se deseja gerenciar
# preco_elepot_referencia = 52700                                                                                 # Preço elepot USD/MW (ref DOI 10.1109/ECCE.2013.6646971)
# # dolar_2013 = 2.15                                                                                             # Cotação do dolar na epoca (google)
# # inflacao_acumulada = 2.0041                                                                                   # Inflacao acumulada entre a epoca e agora (fonte: ibge)
# ppi_2013 = 59.5                                                                                                 # ppi da epoca
# ppi_2026 = 61.058                                                                                               # ppi da epoca
# ppi = ppi_2026 / ppi_2013                                                                                       # razao do ppi
# preco_razao_elepot = (preco_elepot_referencia/1e3) * ppi                                                        # Razao USD/kW


preco_razao_elepot = 10
vetor_preco_razao_elepot = [5, 10, 20]


taxa_disponibilidade = 0.8  # 80% de disponibilidade diária

dias_por_mes = 30  # Considerando 30 dias por mês

# Degradação dos componentes
ciclos_bateria_vida = 5300  # ciclos até 80% da capacidade (Baseado no datasheet da bateria)
horas_supercap_vida = 1000000  # horas até 80% da capacidade (Baseado no datasheet do supercapacitor)

# Parâmetros financeiros para VPL
horizonte_analise_meses = 60  # 5 anos

# Taxa de desconto mensal (ex: 10% ao ano -> 0.10/12)
taxa_desconto_anual = 0.10                                                  # Taxa minima de atratividade anual 

taxa_desconto_mensal = (1 + taxa_desconto_anual) ** (1/12) - 1              # TMA mensal calculada a partir da TMA anual

# Definições relativas a otmização
step_pth = 25                                                                                   # Step entre as potências de limiares simuladas
potencia_de_limiar_max = 2000                                                                   # Potência de limiar máxima
potencia_de_limiar_min = 1000                                                                   # Potência de limiar mínima
min_pth = round(potencia_de_limiar_min / step_pth)                                              # Número discreto mínimo de passos para a potência de limiar
max_pth = round((potencia_de_limiar_max - potencia_de_limiar_min) / step_pth) + min_pth        # Número discreto máximo de passos para a potência de limiar


Ns_b = 16                                                           # Número de baterias em serie
Ns_uc = 16                                                          # Número de supercapacitores em serie

min_Nm_uc = 11                                                      # Número minimo de modulos de supercapacitor
max_Nm_uc = 31                                                      # Número máximo de modulos de supercapacitor (Não extrapolar 1500 V)
min_Np_uc = 0                                                       # Número minimo de supercapacitores em paralelo
max_Np_uc = 7                                                       # Número máximo de supercapacitores em paralelo

min_Nm_b = 15                                                       # Número minimo de modulos de bateria em serie                                                  
max_Nm_b = 28                                                       # Número maximo de modulos de bateria em serie (Não extrapolar 1500 V)
min_Np_b = 0                                                        # Número mínimo de baterias em paralelo
max_Np_b = 8                                                       # Número máximo de baterias em paralelo


vetor_min_Nm_uc = [6, 11, 18]
vetor_min_Nm_b = [8, 15, 22]
# Definição dos parametros do problema
cot_dolar = 5.30                                                   # 22/07/2025
vetor_cot_dolar = [4.58, 5.30, 6.31]                                # Vetor de variacao da cotação do dolar
Pb_usd = 12.8                                                      # Preço da bateria em dolares (Fonte: data_sources.xlsx)
vetor_Pb_uds = [6.4, 12.8, 34.688]                                    # Vetor de sensibilidade do preço da bateria em dolares
Puc_usd = 9.75                                                     # Preço do supercapacitor em dolares (Fonte: data_sources.xlsx)
vetor_Puc_usd = [5.85, 9.75, 13.65]                                  # Vetor de sensibilidade do preço do supercapacitor em dolares



Vb = 0.596                                                          # Volume da bateria em L (Fonte: data_sources.xlsx)
Vuc = 0.496                                                         # Volume do supercapacitor em L (Fonte: data_sources.xlsx)
volume_maximo = (np.pi * (26/2)**2 * 65 * 1e-6) * 41000             # Volume máximo permitido para o projeto. pi * r^2 * h <- volume da bateria de referencia, vezes o numero maximo de baterias de referencias.

Wb = 1.060                                                          # Peso da bateria em kg (Fonte: data_sources.xlsx)
Wuc = 0.460                                                         # Peso do supercapacitor em kg (Fonte: data_sources.xlsx)

Ns_b = 16                                                           # Número de baterias em serie
Ns_uc = 16                                                          # Número de supercapacitores em serie

Cap_b = 40.0                                                        # Capacidade da bateria em Ah
T_xb = 6                                                            # Multiplicador da capacidade da bateria
vetor_T_xb = [2, 6, 10]                                             # Vetor de sensibilidade da capacidade da bateria
Cap_uc = 280.0                                                      # Capacidade do supercapacitor em Ah
T_xuc = 8                                                           # Multiplicador da capacidade do supercapacitor
vetor_T_xuc = variacao * T_xuc                                      # Vetor de sensibilidade da capacidade do supercapacitor

arquivo = "AGREGADOR ANALYSIS.xlsx"
diretorio_figuras = "Figuras/" + arquivo.split(".")[0]
arquivo_excel = diretorio_figuras + "/" f"{arquivo.split(".")[0]}_sensibilidade.xlsx"
os.makedirs(diretorio_figuras, exist_ok=True)
data = "data/" + arquivo
sheet = "Log"


algorithm = NSGA2(
    pop_size=20,
    n_offsprings=20,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.8, eta=10),
    mutation=PM(eta=10, prob=0.4),
    eliminate_duplicates=True
)


termination = get_termination("n_gen", 50)

print(f"Preço do diesel: {preco_diesel} R$    ;       Variação: {vetor_preco_diesel}")
print(f"Cotação do dolar: {cot_dolar} R$/USD  ;       Variação: {vetor_cot_dolar}")
print(f"Eletronica de potencia: {preco_razao_elepot} USD/kW    ;       Variação: {vetor_preco_razao_elepot}")
print(f"Preço bateria: {Pb_usd} USD   ;       Variação: {vetor_Puc_usd}")
print(f"Preço supercapacitor: {Puc_usd} USD   ;       Variação: {vetor_Puc_usd}")
print(f"C-rate da bateria: {T_xb} C   ;       Variação: {vetor_T_xb}")


columns_df = ["Parametro variado", "Preco Diesel [R$]", "Cotacao Dolar", "Preco Razao Elepot [USD]", "Preco R.E. Cor. Dolar [R$]",  "Preco Bat [USD]", "Preco Bat Cor. Dolar [R$]", "Preco UC [USD]", "Preco UC Cor. Dolar [R$]", "C-rate", "Nm_b min", "Nm_uc min", "Nm,b", "Np,b","Nm,uc", "Np,uc", "Volume Total [L]", "Energia Total Bat. [kWh]", "Energia Total UC. [kWh]", "Energia Total [kWh]", "Pth [kW]", "VPL [R$]"]

# Valores de referência (baseline): um parâmetro por vez varia, os demais ficam nesses valores
baseline = {
    "Preco Diesel"       : preco_diesel,
    "Cotacao Dolar"      : cot_dolar,
    "Preco Razao Elepot" : preco_razao_elepot,  # 10
    "Preco Bat"          : Pb_usd,
    "Preco UC"           : Puc_usd,
    "C-rate"             : T_xb,
    "Nm_b min"           : min_Nm_b,
    "Nm_uc min"          : min_Nm_uc
}

# Cada parâmetro e seu vetor de variação (one-at-a-time)
# Exclui o valor do meio de cada vetor (já rodado na simulação original / baseline)
def _vetor_sem_meio(vetor):
    """Remove o elemento do meio (índice len//2); baseline já cobre esse caso."""
    n = len(vetor)
    if n <= 1:
        return vetor
    meio = n // 2
    return [vetor[i] for i in range(n) if i != meio]

variaveis_sensibilidade = [
    ("Preco Diesel", vetor_preco_diesel),
    ("Cotacao Dolar", vetor_cot_dolar),
    ("Preco Razao Elepot", vetor_preco_razao_elepot),
    ("Preco Bat", vetor_Pb_uds),
    ("Preco UC", vetor_Puc_usd),
    ("C-rate", vetor_T_xb),
    ("Nm_b min",  vetor_min_Nm_b),
    ("Nm_uc min", vetor_min_Nm_uc)
]
# Verifica se o arquivo existe
if not os.path.exists(arquivo_excel):
    print("Arquivo não existe. Criando com header...")
    df = pd.DataFrame(columns=columns_df)
    df.to_excel(arquivo_excel, index=False)
else:
    print("Arquivo já existe. Carregando...")
    df = pd.read_excel(arquivo_excel)
    if "Parametro variado" not in df.columns:
        df.insert(0, "Parametro variado", "")

# Configuração fixa a ser avaliada (usada no "Caso base" e nos cenários de config ótima)
CONFIG_OTIMA = {
    "Nm_b": 27,
    "Np_b": 5,
    "Nm_uc": 11,
    "Np_uc": 1,
    "Pth": 1525  # [kW]
}

SoC_uc_ref = 50
BH = 4
Taxa = 0.5


# Incluir "Caso base" (CONFIG_OTIMA com parâmetros padrão) na tabela de sensibilidade, se ainda não existir
# Usa apenas _evaluate (sem otimização), igual ao bloco da config ótima por cenário
if not (df["Parametro variado"] == "Caso base").any():
    print("Incluindo Caso base (config ótima com parâmetros padrão) em _sensibilidade.xlsx...")
    sensibilidade_input_base = dict(baseline)
    preco_diesel_b = sensibilidade_input_base["Preco Diesel"]
    cot_dolar_b = sensibilidade_input_base["Cotacao Dolar"]
    preco_razao_elepot_b = sensibilidade_input_base["Preco Razao Elepot"]
    Pb_usd_b = sensibilidade_input_base["Preco Bat"]
    Puc_usd_b = sensibilidade_input_base["Preco UC"]
    T_xb_b = sensibilidade_input_base["C-rate"]
    min_Nm_b_base = sensibilidade_input_base["Nm_b min"]
    min_Nm_uc_base = sensibilidade_input_base["Nm_uc min"]
    problem_base_sens = MyProblem()
    problem_base_sens.setData(data, sheet)
    problem_base_sens.setParams(sensibilidade_input_base)
    problem_base_sens.configFluxUC2Bat(SoC_uc_ref, BH, Taxa)
    x_fixo_b = np.array([
        CONFIG_OTIMA["Nm_b"],
        CONFIG_OTIMA["Np_b"],
        CONFIG_OTIMA["Nm_uc"],
        CONFIG_OTIMA["Np_uc"],
        CONFIG_OTIMA["Pth"] / step_pth
    ])
    out_b = {}
    problem_base_sens._evaluate(x_fixo_b, out_b)
    vpl_b = -out_b["F"][0]
    best_Nm_b_b = CONFIG_OTIMA["Nm_b"]
    best_Np_b_b = CONFIG_OTIMA["Np_b"]
    best_Nm_uc_b = CONFIG_OTIMA["Nm_uc"]
    best_Np_uc_b = CONFIG_OTIMA["Np_uc"]
    best_Pth_b = CONFIG_OTIMA["Pth"]
    total_bat_b = 16 * best_Nm_b_b * best_Np_b_b
    total_uc_b = 16 * best_Nm_uc_b * best_Np_uc_b
    energia_bat_b = 0.128 * total_bat_b
    energia_sc_b = 0.0039 * total_uc_b
    volume_total_b = (0.596 * total_bat_b) + (0.496 * total_uc_b)
    energia_total_b = energia_bat_b + energia_sc_b
    cache_base = {
        "Parametro variado": "Caso base",
        "Preco Diesel [R$]": preco_diesel_b,
        "Cotacao Dolar": cot_dolar_b,
        "Preco Razao Elepot [USD]": preco_razao_elepot_b,
        "Preco R.E. Cor. Dolar [R$]": preco_razao_elepot_b * cot_dolar_b,
        "Preco Bat [USD]": Pb_usd_b,
        "Preco Bat Cor. Dolar [R$]": Pb_usd_b * cot_dolar_b,
        "Preco UC [USD]": Puc_usd_b,
        "Preco UC Cor. Dolar [R$]": Puc_usd_b * cot_dolar_b,
        "C-rate": T_xb_b,
        "Nm_b min": min_Nm_b_base,
        "Nm_uc min": min_Nm_uc_base,
        "Nm,b": best_Nm_b_b,
        "Np,b": best_Np_b_b,
        "Nm,uc": best_Nm_uc_b,
        "Np,uc": best_Np_uc_b,
        "Volume Total [L]": volume_total_b,
        "Energia Total Bat. [kWh]": energia_bat_b,
        "Energia Total UC. [kWh]": energia_sc_b,
        "Energia Total [kWh]": energia_total_b,
        "Pth [kW]": best_Pth_b,
        "VPL [R$]": vpl_b,
    }
    df = pd.concat([df, pd.DataFrame([cache_base])], ignore_index=True)
    df.to_excel(diretorio_figuras + "/" f"{arquivo.split('.')[0]}_sensibilidade.xlsx", columns=columns_df, index=True)

SoC_uc_ref = 50
BH = 4
Taxa = 0.5
# Sensibilidade one-at-a-time: varia um parâmetro por vez, demais em baseline (sem o valor do meio)
for param_nome, vetor_valores in variaveis_sensibilidade:
    valores_a_rodar = _vetor_sem_meio(vetor_valores)
    for valor in valores_a_rodar:
        sensibilidade_input = dict(baseline)
        sensibilidade_input[param_nome] = valor

        preco_diesel        = sensibilidade_input["Preco Diesel"]
        cot_dolar           = sensibilidade_input["Cotacao Dolar"]
        preco_razao_elepot  = sensibilidade_input["Preco Razao Elepot"]
        Pb_usd              = sensibilidade_input["Preco Bat"]
        Puc_usd             = sensibilidade_input["Preco UC"]
        T_xb                = sensibilidade_input["C-rate"]
        min_Nm_b            = sensibilidade_input["Nm_b min"]
        min_Nm_uc           = sensibilidade_input["Nm_uc min"]

        sensibilidade_cache = {"Parametro variado"               :   param_nome,
                               "Preco Diesel [R$]"              :   None,
                               "Cotacao Dolar"                  :   None,
                               "Preco Razao Elepot [USD]"       :   None,
                               "Preco R.E. Cor. Dolar [R$]"     :   None,
                               "Preco Bat [USD]"                :   None,
                               "Preco Bat Cor. Dolar [R$]"      :   None,
                               "Preco UC [USD]"                 :   None,
                               "Preco UC Cor. Dolar [R$]"       :   None,
                               "C-rate"                         :   None,
                               "Nm_b min"                       :   None,
                               "Nm_uc min"                      :   None,
                               "Nm,b"                           :   None,
                               "Np,b"                           :   None,
                               "Nm,uc"                          :   None,
                               "Np,uc"                          :   None,
                               "Volume Total [L]"               :   None,
                               "Energia Total Bat. [kWh]"       :   None,
                               "Energia Total UC. [kWh]"        :   None,
                               "Energia Total [kWh]"            :   None,
                               "Pth [kW]"                       :   None,
                               "VPL [R$]"                       :   None}
        
        # print(df)

        # print(f"""({df["Parametro variado"]} == {param_nome}) &
        #           ({df["Preco Diesel [R$]"]} == {preco_diesel}) &
        #           ({df["Cotacao Dolar"]} == {cot_dolar}) &
        #           ({df["Preco Razao Elepot [USD]"]} == {preco_razao_elepot}) &
        #           ({df["Preco Bat [USD]"]} == {Pb_usd}) &
        #           ({df["Preco UC [USD]"]} == {Puc_usd}) &
        #           ({df["C-rate"]} == {T_xb}) &
        #           ({df["Nm_b min"]} == {min_Nm_b}) & 
        #           ({df["Nm_uc min"]} == {min_Nm_uc}) """)

        filtro = (
            (df["Parametro variado"] == param_nome) &
            (df["Preco Diesel [R$]"] == preco_diesel) &
            (df["Cotacao Dolar"] == cot_dolar) &
            (df["Preco Razao Elepot [USD]"] == preco_razao_elepot) &
            (df["Preco Bat [USD]"] == Pb_usd) &
            (df["Preco UC [USD]"] == Puc_usd) &
            (df["C-rate"] == T_xb) &
            (df["Nm_b min"] == min_Nm_b) & 
            (df["Nm_uc min"] == min_Nm_uc) 
        )
        # print(filtro)

        if filtro.any():
            print("Já existe, pulando:", param_nome, "=", valor)
            continue

        print("Novo caso, calculando:", sensibilidade_input)

       

        problem = MyProblem()
        problem.setData(data, sheet)
        problem.setParams(sensibilidade_input)
        problem.configFluxUC2Bat(SoC_uc_ref, BH, Taxa)
        Pb = Pb_usd * cot_dolar     # Preço da bateria em reais
        Puc = Puc_usd * cot_dolar   # Preço do supercapacitor em reais

        res = minimize(problem,
                algorithm,
                termination,
                seed=1,
                save_history=True,
                verbose=True)

        X = res.X
        F = res.F
        problem.simulation_cache = {}

        print(f'X: {X}')
        print(f'F: {F}')
        try:
            idx_best = np.argmin(F[:, 0])  # Menor valor negativo de F => maior VPL
            best_Nm_b = int(round(X[idx_best, 0]))
            best_Np_b = int(round(X[idx_best, 1]))
            best_Nm_uc = int(round(X[idx_best, 2]))
            best_Np_uc = int(round(X[idx_best, 3]))
            best_Pth = step_pth * int(round(X[idx_best, 4]))
        except:
            idx_best = np.argmin(F[0])
            best_Nm_b = int(round(X[0]))
            best_Np_b = int(round(X[1]))
            best_Nm_uc = int(round(X[2]))
            best_Np_uc = int(round(X[3]))
            best_Pth = step_pth * int(round(X[4]))

        vpl = 0
        for i, fc in enumerate(problem.melhor_fluxo_caixa):
            vpl += fc / ((1 + taxa_desconto_mensal) ** i)

        total_bat = 16 * best_Nm_b * best_Np_b
        total_uc  = 16 * best_Nm_uc * best_Np_uc
        energia_bat = 0.128 * total_bat
        energia_sc = 0.0039 * total_uc
        volume_total = (0.596 * total_bat) + (0.496 * total_uc)
        energia_total = energia_bat + energia_sc
        sensibilidade_cache["Preco Diesel [R$]"] = preco_diesel
        sensibilidade_cache["Cotacao Dolar"] = cot_dolar
        sensibilidade_cache["Preco Razao Elepot [USD]"] = preco_razao_elepot
        sensibilidade_cache["Preco R.E. Cor. Dolar [R$]"] = preco_razao_elepot * cot_dolar
        sensibilidade_cache["Preco Bat [USD]"] = Pb_usd
        sensibilidade_cache["Preco Bat Cor. Dolar [R$]"] = Pb_usd * cot_dolar
        sensibilidade_cache["Preco UC [USD]"] = Puc_usd
        sensibilidade_cache["Preco UC Cor. Dolar [R$]"] = Puc_usd * cot_dolar
        sensibilidade_cache["C-rate"] = T_xb
        sensibilidade_cache["Nm_b min"] = min_Nm_b
        sensibilidade_cache["Nm_uc min"] = min_Nm_uc
        sensibilidade_cache["Nm,b"] = best_Nm_b
        sensibilidade_cache["Np,b"] = best_Np_b
        sensibilidade_cache["Nm,uc"] = best_Nm_uc
        sensibilidade_cache["Np,uc"] = best_Np_uc
        sensibilidade_cache["Volume Total [L]"] = volume_total
        sensibilidade_cache["Energia Total Bat. [kWh]"] = energia_bat
        sensibilidade_cache["Energia Total UC. [kWh]"] = energia_sc
        sensibilidade_cache["Energia Total [kWh]"] = energia_total
        sensibilidade_cache["Pth [kW]"] = best_Pth
        sensibilidade_cache["VPL [R$]"] = vpl

        res.X = None
        res.F = None
        res.G = None

        df = pd.concat([df, pd.DataFrame([sensibilidade_cache])], ignore_index=True)
        df.to_excel(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_sensibilidade.xlsx", columns=columns_df, index=True)





# ----------------------------------------------------------------------------------------------------------------------
# Avaliação de uma configuração específica (fixa) em todos os cenários de sensibilidade
# ----------------------------------------------------------------------------------------------------------------------

arquivo_excel_config = diretorio_figuras + "/" f"{arquivo.split('.')[0]}_sensibilidade_configuracao_otima.xlsx"

if not os.path.exists(arquivo_excel_config):
    df_config = pd.DataFrame(columns=columns_df)
    df_config.to_excel(arquivo_excel_config, index=False)
else:
    df_config = pd.read_excel(arquivo_excel_config)


for param_nome, vetor_valores in variaveis_sensibilidade:
    valores_a_rodar = _vetor_sem_meio(vetor_valores)
    for valor in valores_a_rodar:
        sensibilidade_input = dict(baseline)
        sensibilidade_input[param_nome] = valor

        preco_diesel        = sensibilidade_input["Preco Diesel"]
        cot_dolar           = sensibilidade_input["Cotacao Dolar"]
        preco_razao_elepot  = sensibilidade_input["Preco Razao Elepot"]
        Pb_usd              = sensibilidade_input["Preco Bat"]
        Puc_usd             = sensibilidade_input["Preco UC"]
        T_xb                = sensibilidade_input["C-rate"]
        min_Nm_b            = sensibilidade_input["Nm_b min"]
        min_Nm_uc           = sensibilidade_input["Nm_uc min"]

        filtro_cfg = (
            (df_config["Parametro variado"] == param_nome) &
            (df_config["Preco Diesel [R$]"] == preco_diesel) &
            (df_config["Cotacao Dolar"] == cot_dolar) &
            (df_config["Preco Razao Elepot [USD]"] == preco_razao_elepot) &
            (df_config["Preco Bat [USD]"] == Pb_usd) &
            (df_config["Preco UC [USD]"] == Puc_usd) &
            (df_config["C-rate"] == T_xb) &
            (df_config["Nm_b min"] == min_Nm_b) &
            (df_config["Nm_uc min"] == min_Nm_uc)
        )

        if filtro_cfg.any():
            print("Configuração ótima já existe, pulando:", param_nome, "=", valor)
            continue

        print("Novo caso (configuração ótima), calculando:", sensibilidade_input)

        problem_caso = MyProblem()
        problem_caso.setData(data, sheet)
        problem_caso.setParams(sensibilidade_input)
        problem_caso.configFluxUC2Bat(SoC_uc_ref, BH, Taxa)

        x_fixo = np.array([
            CONFIG_OTIMA["Nm_b"],
            CONFIG_OTIMA["Np_b"],
            CONFIG_OTIMA["Nm_uc"],
            CONFIG_OTIMA["Np_uc"],
            CONFIG_OTIMA["Pth"] / step_pth
        ])

        out = {}
        problem_caso._evaluate(x_fixo, out)
        vpl = -out["F"][0]

        best_Nm_b = CONFIG_OTIMA["Nm_b"]
        best_Np_b = CONFIG_OTIMA["Np_b"]
        best_Nm_uc = CONFIG_OTIMA["Nm_uc"]
        best_Np_uc = CONFIG_OTIMA["Np_uc"]
        best_Pth = CONFIG_OTIMA["Pth"]

        total_bat = 16 * best_Nm_b * best_Np_b
        total_uc  = 16 * best_Nm_uc * best_Np_uc
        energia_bat = 0.128 * total_bat
        energia_sc = 0.0039 * total_uc
        volume_total = (0.596 * total_bat) + (0.496 * total_uc)
        energia_total = energia_bat + energia_sc

        sensibilidade_cfg = {
            "Parametro variado"               : param_nome,
            "Preco Diesel [R$]"              : preco_diesel,
            "Cotacao Dolar"                  : cot_dolar,
            "Preco Razao Elepot [USD]"       : preco_razao_elepot,
            "Preco R.E. Cor. Dolar [R$]"     : preco_razao_elepot * cot_dolar,
            "Preco Bat [USD]"                : Pb_usd,
            "Preco Bat Cor. Dolar [R$]"      : Pb_usd * cot_dolar,
            "Preco UC [USD]"                 : Puc_usd,
            "Preco UC Cor. Dolar [R$]"       : Puc_usd * cot_dolar,
            "C-rate"                         : T_xb,
            "Nm_b min"                       : min_Nm_b,
            "Nm_uc min"                      : min_Nm_uc,
            "Nm,b"                           : best_Nm_b,
            "Np,b"                           : best_Np_b,
            "Nm,uc"                          : best_Nm_uc,
            "Np,uc"                          : best_Np_uc,
            "Volume Total [L]"               : volume_total,
            "Energia Total Bat. [kWh]"       : energia_bat,
            "Energia Total UC. [kWh]"        : energia_sc,
            "Energia Total [kWh]"            : energia_total,
            "Pth [kW]"                       : best_Pth,
            "VPL [R$]"                       : vpl
        }

        df_config = pd.concat([df_config, pd.DataFrame([sensibilidade_cfg])], ignore_index=True)
        df_config.to_excel(arquivo_excel_config, columns=columns_df, index=False)


# ----------------------------------------------------------------------------------------------------------------------
# Tabela de comparação: caso base (config ótima com parâmetros padrão [1]) vs cenários (com % de variação)
# ----------------------------------------------------------------------------------------------------------------------

# Parâmetros padrão = posição [1] em cada vetor (mesmo que baseline)
params_padrao = dict(baseline)

problem_base = MyProblem()
problem_base.setData(data, sheet)
problem_base.setParams(params_padrao)
problem_base.configFluxUC2Bat(SoC_uc_ref, BH, Taxa)
x_fixo = np.array([
    CONFIG_OTIMA["Nm_b"],
    CONFIG_OTIMA["Np_b"],
    CONFIG_OTIMA["Nm_uc"],
    CONFIG_OTIMA["Np_uc"],
    CONFIG_OTIMA["Pth"] / step_pth
])
out_base = {}
problem_base._evaluate(x_fixo, out_base)
vpl_base = -out_base["F"][0]

preco_diesel_p = params_padrao["Preco Diesel"]
cot_dolar_p = params_padrao["Cotacao Dolar"]
preco_razao_elepot_p = params_padrao["Preco Razao Elepot"]
Pb_usd_p = params_padrao["Preco Bat"]
Puc_usd_p = params_padrao["Preco UC"]
T_xb_p = params_padrao["C-rate"]
min_Nm_b_p = params_padrao["Nm_b min"]
min_Nm_uc_p = params_padrao["Nm_uc min"]

total_bat_b = 16 * CONFIG_OTIMA["Nm_b"] * CONFIG_OTIMA["Np_b"]
total_uc_b = 16 * CONFIG_OTIMA["Nm_uc"] * CONFIG_OTIMA["Np_uc"]
energia_bat_b = 0.128 * total_bat_b
energia_sc_b = 0.0039 * total_uc_b
volume_total_b = (0.596 * total_bat_b) + (0.496 * total_uc_b)
energia_total_b = energia_bat_b + energia_sc_b

caso_base_row = {
    "Parametro variado"               : "Caso base",
    "Preco Diesel [R$]"              : preco_diesel_p,
    "Cotacao Dolar"                  : cot_dolar_p,
    "Preco Razao Elepot [USD]"       : preco_razao_elepot_p,
    "Preco R.E. Cor. Dolar [R$]"     : preco_razao_elepot_p * cot_dolar_p,
    "Preco Bat [USD]"                : Pb_usd_p,
    "Preco Bat Cor. Dolar [R$]"      : Pb_usd_p * cot_dolar_p,
    "Preco UC [USD]"                 : Puc_usd_p,
    "Preco UC Cor. Dolar [R$]"       : Puc_usd_p * cot_dolar_p,
    "C-rate"                         : T_xb_p,
    "Nm_b min"                       : min_Nm_b_p,
    "Nm_uc min"                      : min_Nm_uc_p,
    "Nm,b"                           : CONFIG_OTIMA["Nm_b"],
    "Np,b"                           : CONFIG_OTIMA["Np_b"],
    "Nm,uc"                          : CONFIG_OTIMA["Nm_uc"],
    "Np,uc"                          : CONFIG_OTIMA["Np_uc"],
    "Volume Total [L]"               : volume_total_b,
    "Energia Total Bat. [kWh]"        : energia_bat_b,
    "Energia Total UC. [kWh]"         : energia_sc_b,
    "Energia Total [kWh]"             : energia_total_b,
    "Pth [kW]"                       : CONFIG_OTIMA["Pth"],
    "VPL [R$]"                       : vpl_base
}

def _fmt_celula_comparacao(val, base_val, col):
    """Formata valor com percentual de variação em relação ao caso base (↑ ou ↓)."""
    if col == "Parametro variado":
        return val
    base_num = base_val
    try:
        v = float(val)
        b = float(base_num)
    except (TypeError, ValueError):
        return val
    if v == b:
        return val
    if b == 0:
        return f"{v} (↑ --%)" if v > 0 else f"{v} (↓ --%)"
    pct = (v - b) / b * 100
    if pct > 0:
        return f"{v} (↑ {pct:.1f}%)"
    return f"{v} (↓ {-pct:.1f}%)"

# Montar tabela: primeira linha = caso base; demais = df_config com células com % quando diferente do base
linhas_comparacao = [caso_base_row]
for _, row in df_config.iterrows():
    nova_linha = {}
    for col in columns_df:
        base_val = caso_base_row[col]
        val = row[col]
        nova_linha[col] = _fmt_celula_comparacao(val, base_val, col)
    linhas_comparacao.append(nova_linha)

df_comparacao = pd.DataFrame(linhas_comparacao)
arquivo_comparacao = diretorio_figuras + "/" + arquivo.split(".")[0] + "_sensibilidade_comparacao.xlsx"
df_comparacao.to_excel(arquivo_comparacao, index=False, columns=columns_df)
print(f"Tabela de comparação salva em: {arquivo_comparacao}")


# ----------------------------------------------------------------------------------------------------------------------
# Tabela de comparação ÓTIMOS: caso base = config ótima com params padrão; linhas = config ótima por cenário (com %)
# Lê o caso base da tabela _sensibilidade.xlsx (evita rodar a otimização de novo).
# ----------------------------------------------------------------------------------------------------------------------

df_sens = pd.read_excel(arquivo_excel)
tem_caso_base = (df_sens["Parametro variado"] == "Caso base").any()
if tem_caso_base:
    caso_base_otimo_row = df_sens.loc[df_sens["Parametro variado"] == "Caso base"].iloc[0].to_dict()
    df_resto = df_sens[df_sens["Parametro variado"] != "Caso base"]
else:
    caso_base_otimo_row = None
    df_resto = df_sens

if caso_base_otimo_row is not None:
    linhas_comparacao_otimos = [caso_base_otimo_row]
    for _, row in df_resto.iterrows():
        nova_linha = {}
        for col in columns_df:
            base_val = caso_base_otimo_row[col]
            val = row[col]
            nova_linha[col] = _fmt_celula_comparacao(val, base_val, col)
        linhas_comparacao_otimos.append(nova_linha)
    df_comparacao_otimos = pd.DataFrame(linhas_comparacao_otimos)
    arquivo_comparacao_otimos = diretorio_figuras + "/" + arquivo.split(".")[0] + "_sensibilidade_comparacao_otimos.xlsx"
    df_comparacao_otimos.to_excel(arquivo_comparacao_otimos, index=False, columns=columns_df)
    print(f"Tabela de comparação (ótimos) salva em: {arquivo_comparacao_otimos}")
else:
    print("Aviso: 'Caso base' não encontrado em _sensibilidade.xlsx. Rode a sensibilidade antes para gerar a tabela de ótimos.")
