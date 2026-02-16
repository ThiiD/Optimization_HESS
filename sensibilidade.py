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
preco_diesel = 6.00
vetor_preco_diesel = [3.69, 5.78, 7.46]                                                                         # R$/litro
rendimento_diesel = 3.0                                                                                         # kWh/litro

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
step_pth = 25                                                       # Step entre as potências de limiares simuladas
potencia_de_limiar_max = 2000                                       # Potência de limiar máxima
max_pth = round(potencia_de_limiar_max / step_pth)                  # Número discreto máximo de passos para a potência de limiar
min_pth = 0                                                         # Número discreto mínimo de passos para a potência de limiar

min_uc = 0                                                          # Número minimo de supercapacitores
max_uc = 10                                                         # Número máximo de supercapacitores

min_bat = 0                                                         # Número mínimo de baterias
max_bat = 10                                                        # Número máximo de baterias

# Definição dos parametros do problema
cot_dolar = 5.57                                                    # 22/07/2025
vetor_cot_dolar = [4.58, 5.30, 6.31]                                # Vetor de variacao da cotação do dolar
Pb_usd = 28.00                                                      # Preço da bateria em dolares (Fonte: data_sources.xlsx)
vetor_Pb_uds = [6.4, 12.8, 34.688]                                    # Vetor de sensibilidade do preço da bateria em dolares
Puc_usd = 53.75                                                     # Preço do supercapacitor em dolares (Fonte: data_sources.xlsx)
vetor_Puc_usd = [5.85, 9.75, 13.65]                                  # Vetor de sensibilidade do preço do supercapacitor em dolares



Vb = 0.596                                                          # Volume da bateria em L (Fonte: data_sources.xlsx)
Vuc = 0.496                                                         # Volume do supercapacitor em L (Fonte: data_sources.xlsx)

Wb = 1.060                                                          # Peso da bateria em kg (Fonte: data_sources.xlsx)
Wuc = 0.460                                                         # Peso do supercapacitor em kg (Fonte: data_sources.xlsx)

Ns_b = 16                                                           # Número de baterias em serie
Nm_b = 24                                                           # Número de módulos de baterias
Ns_uc = 16                                                          # Número de supercapacitores em serie
Nm_uc = 20                                                          # Número de módulos de supercapacitores

Cap_b = 40.0                                                        # Capacidade da bateria em Ah
T_xb = 6                                                            # Multiplicador da capacidade da bateria
vetor_T_xb = [2, 6, 10]                                        # Vetir de sensibilidade da capacidade da bateria
Cap_uc = 280.0                                                      # Capacidade do supercapacitor em Ah
T_xuc = 8                                                           # Multiplicador da capacidade do supercapacitor
vetor_T_xuc = variacao * T_xuc                                      # Vetor de sensibilidade da capacidade do supercapacitor

arquivo = "UMAX_18-10-24.xlsx"
diretorio_figuras = "Figuras/" + arquivo.split(".")[0]
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


termination = get_termination("n_gen", 10)

sensibilidade_cache = {"Preco Diesel"           :   [],
                       "Cotacao Dolar"          :   [],
                       "Preco Razao Elepot"     :   [],
                       "Preco R.E. Cor. Dolar"  :   [],
                       "Preco Bat"              :   [],
                       "Preco Bat Cor. Dolar"   :   [],
                       "Preco UC"               :   [],
                       "Preco UC Cor. Dolar"    :   [],
                       "C-rate"                 :   [],
                       "Np,b"                   :   [],
                       "Np,uc"                  :   [],
                       "Pth"                    :   [],
                       "VPL"                    :   []}


print(f"Preço do diesel: {preco_diesel} R$    ;       Variação: {vetor_preco_diesel}")
print(f"Cotação do dolar: {cot_dolar} R$/USD  ;       Variação: {vetor_cot_dolar}")
print(f"Eletronica de potencia: {preco_razao_elepot} USD/kW    ;       Variação: {vetor_preco_razao_elepot}")
print(f"Preço bateria: {Pb_usd} USD   ;       Variação: {vetor_Puc_usd}")
print(f"Preço supercapacitor: {Puc_usd} USD   ;       Variação: {vetor_Puc_usd}")
print(f"C-rate da bateria: {T_xb} C   ;       Variação: {vetor_T_xb}")





for preco_diesel in vetor_preco_diesel:
    for cot_dolar in vetor_cot_dolar:
        for preco_razao_elepot in vetor_preco_razao_elepot:
            for Pb_usd in vetor_Pb_uds:
                for Puc_usd in vetor_Puc_usd:
                    for T_xb in vetor_T_xb:

                        sensibilidade_input = {"Preco Diesel"       :   preco_diesel,
                                            "Cotacao Dolar"      :   cot_dolar,
                                            "Preco Razao Elepot" :   preco_razao_elepot,
                                            "Preco Bat"          :   Pb_usd,
                                            "Preco UC"           :   Puc_usd,
                                            "C-rate"             :   T_xb}
                        problem = MyProblem()
                        problem.setData(data, sheet)
                        problem.setParams(sensibilidade_input)
                        Pb = Pb_usd * cot_dolar     # Preço da bateria em reais
                        Puc = Puc_usd * cot_dolar   # Preço do supercapacitor em reais

                        outputDisplay = MyOutput(diretorio_figuras + "/" + f"{arquivo.split(".")[0]}_nada.csv")
                        res = minimize(problem,
                                algorithm,
                                termination,
                                seed=1,
                                save_history=True,
                                verbose=True,
                                output=outputDisplay)

                        # Após a otimização
                        X = res.X
                        F = res.F
                        problem.simulation_cache = {}

                        print(f'X: {X}')
                        print(f'F: {F}')
                        outputDisplay.finalize()


                        try:
                            idx_best = np.argmin(F[:, 0])  # Menor valor negativo de F => maior VPL
                            best_Np_b = int(round(X[idx_best, 0]))
                            best_Np_uc = int(round(X[idx_best, 1]))
                            best_Pth = step_pth * int(round(X[idx_best, 2]))
                        except:
                            idx_best = np.argmin(F[0])  # Menor valor negativo de F => maior VPL
                            best_Np_b = int(round(X[0]))
                            best_Np_uc = int(round(X[1]))
                            best_Pth = step_pth * int(round(X[2]))

                        vpl = 0
                        for i, fc in enumerate(problem.melhor_fluxo_caixa):
                            vpl += fc / ((1 + taxa_desconto_mensal) ** i)
                        
                        sensibilidade_cache["Preco Diesel"].append(preco_diesel)
                        sensibilidade_cache["Cotacao Dolar"].append(cot_dolar)
                        sensibilidade_cache["Preco Razao Elepot"].append(preco_razao_elepot)
                        sensibilidade_cache["Preco R.E. Cor. Dolar"].append(preco_razao_elepot * cot_dolar)
                        sensibilidade_cache["Preco Bat"].append(Pb)
                        sensibilidade_cache["Preco Bat Cor. Dolar"].append(Pb * cot_dolar)
                        sensibilidade_cache["Preco UC"].append(Puc)
                        sensibilidade_cache["Preco UC Cor. Dolar"].append(Puc * cot_dolar)
                        sensibilidade_cache["C-rate"].append(T_xb)
                        sensibilidade_cache["Np,b"].append(best_Np_b)
                        sensibilidade_cache["Np,uc"].append(best_Np_uc)
                        sensibilidade_cache["Pth"].append(best_Pth)
                        sensibilidade_cache["VPL"].append(vpl)

                        res.X = None
                        res.F = None




columns_df = ["Preco Diesel", "Cotacao Dolar", "Preco Razao Elepot", "Preco R.E. Cor. Dolar",  "Preco Bat", "Preco Bat Cor. Dolar", "Preco UC", "Preco UC Cor. Dolar", "C-rate", "Np,b", "Np,uc", "Pth", "VPL"]
df = pd.DataFrame(sensibilidade_cache, columns = columns_df)
df.to_excel(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_sensibilidade.xlsx", columns=columns_df)

print(df)

    