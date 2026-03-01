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
preco_elepot_referencia = 52700                                                                                 # Preço elepot USD/MW (ref DOI 10.1109/ECCE.2013.6646971)
# dolar_2013 = 2.15                                                                                             # Cotação do dolar na epoca (google)
# inflacao_acumulada = 2.0041                                                                                   # Inflacao acumulada entre a epoca e agora (fonte: ibge)
ppi_2013 = 59.5                                                                                                 # ppi da epoca
ppi_2026 = 61.058                                                                                               # ppi da epoca
ppi = ppi_2026 / ppi_2013                                                                                       # razao do ppi
preco_razao_elepot = (preco_elepot_referencia/1e3) * ppi                                                        # Razao USD/kW

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

arquivo = "CR-3112_28-09-24_AGGREGATED.xlsx"
diretorio_figuras = "Figuras/" + arquivo.split(".")[0]
arquivo_excel = diretorio_figuras + "/" f"{arquivo.split(".")[0]}_sensibilidade.xlsx"
os.makedirs(diretorio_figuras, exist_ok=True)
data = "data/" + arquivo
sheet = "Log"


algorithm = NSGA2(
    pop_size=20,
    n_offsprings=20,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=15),
    mutation=PM(eta=15, prob=0.2),
    eliminate_duplicates=True
)


termination = get_termination("n_gen", 15)

print(f"Preço do diesel: {preco_diesel} R$    ;       Variação: {vetor_preco_diesel}")
print(f"Cotação do dolar: {cot_dolar} R$/USD  ;       Variação: {vetor_cot_dolar}")
print(f"Eletronica de potencia: {preco_razao_elepot} USD/kW    ;       Variação: {vetor_preco_razao_elepot}")
print(f"Preço bateria: {Pb_usd} USD   ;       Variação: {vetor_Puc_usd}")
print(f"Preço supercapacitor: {Puc_usd} USD   ;       Variação: {vetor_Puc_usd}")
print(f"C-rate da bateria: {T_xb} C   ;       Variação: {vetor_T_xb}")


columns_df = ["Preco Diesel [R$]", "Cotacao Dolar", "Preco Razao Elepot [USD]", "Preco R.E. Cor. Dolar [R$]",  "Preco Bat [USD]", "Preco Bat Cor. Dolar [R$]", "Preco UC [USD]", "Preco UC Cor. Dolar [R$]", "C-rate", "Nm,b", "Np,b","Nm,uc", "Np,uc", "Volume Total [L]", "Energia Total Bat. [kWh]", "Energia Total UC. [kWh]", "Energia Total [kWh]", "Pth [kW]", "VPL [R$]"]
# Verifica se o arquivo existe
if not os.path.exists(arquivo_excel):
    print("Arquivo não existe. Criando com header...")
    df = pd.DataFrame(columns=columns_df)
    df.to_excel(arquivo_excel, index=False)
else:
    print("Arquivo já existe. Carregando...")
    df = pd.read_excel(arquivo_excel)



def definitions():

    # ------------------------------------------------------
    # ----------------------- Diesel -----------------------
    # ------------------------------------------------------
    preco_diesel = 5.78
    vetor_preco_diesel = [3.69, 5.78, 7.46]                                                                         # R$/litro

    # ------------------------------------------------------
    # ----------------------- Elepot -----------------------
    # ------------------------------------------------------
    preco_razao_elepot = 10
    vetor_preco_razao_elepot = [5, 10, 20]

    # ------------------------------------------------------
    # ----------------------- Dolar ------------------------
    # ------------------------------------------------------
    cot_dolar = 5.30                                                   # 22/07/2025
    vetor_cot_dolar = [4.58, 5.30, 6.31]                                # Vetor de variacao da cotação do dolar
    
    # ------------------------------------------------------
    # ----------------------- Bateria ----------------------
    # ------------------------------------------------------
    Pb_usd = 12.8                                                      # Preço da bateria em dolares (Fonte: data_sources.xlsx)
    vetor_Pb_uds = [6.4, 12.8, 34.688]                                    # Vetor de sensibilidade do preço da bateria em dolares
    
    # ------------------------------------------------------
    # ------------------- Supercapacitor -------------------
    # ------------------------------------------------------
    Puc_usd = 9.75                                                     # Preço do supercapacitor em dolares (Fonte: data_sources.xlsx)
    vetor_Puc_usd = [5.85, 9.75, 13.65]                                  # Vetor de sensibilidade do preço do supercapacitor em dolares

    # ------------------------------------------------------
    # --------------------- C-Rate Bat ---------------------
    # ------------------------------------------------------
    T_xb = 6                                                            # Multiplicador da capacidade da bateria
    vetor_T_xb = [2, 6, 10]                                             # Vetor de sensibilidade da capacidade da bateria







for preco_diesel in vetor_preco_diesel:
    for cot_dolar in vetor_cot_dolar:
        for preco_razao_elepot in vetor_preco_razao_elepot:
            for Pb_usd in vetor_Pb_uds:
                for Puc_usd in vetor_Puc_usd:
                    for T_xb in vetor_T_xb:

                        sensibilidade_input = {"Preco Diesel"       :   preco_diesel,
                                            "Cotacao Dolar"         :   cot_dolar,
                                            "Preco Razao Elepot"    :   preco_razao_elepot,
                                            "Preco Bat"             :   Pb_usd,
                                            "Preco UC"              :   Puc_usd,
                                            "C-rate"                :   T_xb}
                        
                        sensibilidade_cache = {"Preco Diesel [R$]"              :   None,
                                               "Cotacao Dolar"                  :   None,
                                               "Preco Razao Elepot [USD]"       :   None,
                                               "Preco R.E. Cor. Dolar [R$]"     :   None,
                                               "Preco Bat [USD]"                :   None,
                                               "Preco Bat Cor. Dolar [R$]"      :   None,
                                               "Preco UC [USD]"                 :   None,
                                               "Preco UC Cor. Dolar [R$]"       :   None,
                                               "C-rate"                         :   None,
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
                        
                        filtro = (
                            (df["Preco Diesel [R$]"] == preco_diesel) &
                            (df["Cotacao Dolar"] == cot_dolar) &
                            (df["Preco Razao Elepot [USD]"] == preco_razao_elepot) &
                            (df["Preco Bat [USD]"] == Pb_usd) &
                            (df["Preco UC [USD]"] == Puc_usd) &
                            (df["C-rate"] == T_xb)
                        )

                        
                        
                        if filtro.any():
                            print("Já existe, pulando:", preco_diesel, cot_dolar, preco_razao_elepot, Pb_usd, Puc_usd, T_xb)
                            continue


                        print("Novo caso, calculando:", sensibilidade_input)


                        problem = MyProblem()
                        problem.setData(data, sheet)
                        problem.setParams(sensibilidade_input)
                        Pb = Pb_usd * cot_dolar     # Preço da bateria em reais
                        Puc = Puc_usd * cot_dolar   # Preço do supercapacitor em reais

                        # outputDisplay = MyOutput(diretorio_figuras + "/" + f"{arquivo.split(".")[0]}_nada.csv")
                        res = minimize(problem,
                                algorithm,
                                termination,
                                seed=1,
                                save_history=True,
                                verbose=True)

                        # Após a otimização
                        X = res.X
                        F = res.F
                        problem.simulation_cache = {}

                        print(f'X: {X}')
                        print(f'F: {F}')
                        # outputDisplay.finalize()


                        try:
                            idx_best = np.argmin(F[:, 0])  # Menor valor negativo de F => maior VPL
                            best_Nm_b = int(round(X[idx_best, 0]))
                            best_Np_b = int(round(X[idx_best, 1]))
                            best_Nm_uc = int(round(X[idx_best, 2]))
                            best_Np_uc = int(round(X[idx_best, 3]))
                            best_Pth = step_pth * int(round(X[idx_best, 4]))
                        except:
                            idx_best = np.argmin(F[0])  # Menor valor negativo de F => maior VPL
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
                        df.to_excel(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_sensibilidade.xlsx", columns=columns_df)






# df = pd.DataFrame(sensibilidade_cache, columns = columns_df)
# df.to_excel(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_sensibilidade.xlsx", columns=columns_df)

# print(df)

# try:
#     print(f'Arquivo: {arquivo}')
# except:
#     pass
    