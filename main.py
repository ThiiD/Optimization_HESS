import numpy as np
import matplotlib.pyplot as plt
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2

from pymoo.core.problem import ElementwiseProblem

from simulation import Simulation

# Parâmetros financeiros e operacionais
preco_diesel = 6.00  # R$/litro
rendimento_diesel = 3.0  # kWh/litro

taxa_disponibilidade = 0.8  # 80% de disponibilidade diária
duracao_ciclo_horas = 0.5  # 30 minutos por ciclo

dias_por_mes = 30  # Considerando 30 dias por mês

# Degradação dos componentes
ciclos_bateria_vida = 10000  # ciclos até 80% da capacidade
horas_supercap_vida = 100000  # horas até 80% da capacidade

# Parâmetros financeiros para VPL
horizonte_analise_meses = 12  # 10 anos

# Taxa de desconto mensal (ex: 10% ao ano -> 0.10/12)
taxa_desconto_anual = 0.10                                                  # Taxa minima de atratividade anual 

taxa_desconto_mensal = (1 + taxa_desconto_anual) ** (1/12) - 1              # TMA mensal calculada a partir da TMA anual

# Definição dos parametros do problema
cot_dolar = 5.57            # 22/07/2025
Pb_usd = 28.00              # Preço da bateria em dolares (Fonte: data_sources.xlsx)
Puc_usd = 53.75             # Preço do supercapacitor em dolares (Fonte: data_sources.xlsx)

Pb = Pb_usd * cot_dolar     # Preço da bateria em reais
Puc = Puc_usd * cot_dolar   # Preço do supercapacitor em reais

Vb = 0.596                  # Volume da bateria em L (Fonte: data_sources.xlsx)
Vuc = 0.00837               # Volume do supercapacitor em L (Fonte: data_sources.xlsx)

Wb = 1.060                  # Peso da bateria em kg (Fonte: data_sources.xlsx)
Wuc = 0.460                 # Peso do supercapacitor em kg (Fonte: data_sources.xlsx)

Ns_b = 16                   # Número de baterias em serie
Nm_b = 24                   # Número de módulos de baterias
Ns_uc = 16                  # Número de supercapacitores em serie
Nm_uc = 20                  # Número de módulos de supercapacitores

Cap_b = 40.0                # Capacidade da bateria em Ah
T_xb = 6                    # Multiplicador da capacidade da bateria
Cap_uc = 280.0              # Capacidade do supercapacitor em Ah
T_xuc = 3                   # Multiplicador da capacidade do supercapacitor


# Definição do problema de otimização
# A principio, Np_b (número de baterias em paralelo) e Np_uc (número de supercapacitores em paralelo) são variáveis de decisão
# A principio, o problema é definido como um problema de otimização multiobjetivo, em que o objetivo é minimizar o custo total, o volume total e o peso total do sistema de armazenamento de energia
# Posteriormente, irá entrar como variavel de decisão o threshold de potência, que influenciará na energia rejeitada.
# A variação de DoD também entrará como valores de saída do problema de otimização

# Entradas do problema:
#   Np_b: número de baterias em paralelo
#   Np_uc: número de supercapacitores em paralelo
#   Pth: threshold de potência (em W) - valor de decisão

# Saídas do problema:
#   Custo_total: custo total do sistema de armazenamento de energia (em dolares)
#   Volume_total: volume total do sistema de armazenamento de energia (em L)
#   Peso_total: peso total do sistema de armazenamento de energia (em kg)
#   I_bmax: corrente máxima da bateria (em A)
#   I_ucmax: corrente máxima do supercapacitor (em A)
#   E_rej: energia rejeitada pelo sistema de armazenamento de energia (em kWh)
#   DoD_bat: Variação do Depth of Discharge da bateria
#   DoD_uc: Variação do Depth of Discharge do supercapacitor

# Equações do problema:
#   min Pt = (Np_b * Nm_b * Ns_b) * Pb + (Np_uc * Nm_uc * Ns_uc) * Puc
#   min Vt = (Np_b * Nm_b * Ns_b) * Vb + (Np_uc * Nm_uc * Ns_uc) * Vuc
#   min Wt = (Np_b * Nm_b * Ns_b) * Wb + (Np_uc * Nm_uc * Ns_uc) * Wuc
#   max It = (Np_b * Cap_b * T_xb) + (Np_uc * Cap_uc * T_xuc)
#   s.a

        
#   E_rej = (Np_b * Nm_b * Ns_b) * Pb * (1 - DoD_bat) + (Np_uc * Nm_uc * Ns_uc) * Puc * (1 - DoD_uc)
#   DoD_bat = (Np_b * Nm_b * Ns_b) * Pb / ((Np_b * Nm_b * Ns_b) * Pb + (Np_uc * Nm_uc * Ns_uc) * Puc)


class MyProblem(ElementwiseProblem):

    def __init__(self):
        super().__init__(n_var=2,  # Np_b e Np_uc
                         n_obj=1,   # Agora apenas VPL
                         n_ieq_constr=0,  # Sem restrições
                         xl=np.array([1, 1]),  # Mínimo de 1 para cada variável
                         xu=np.array([10, 10]),  # Máximo de 10 para cada variável
                         type_var=np.int64)  # Especificando que as variáveis são inteiros
        self.simulation_cache = {}

    def _evaluate(self, x, out, *args, **kwargs):
        Np_b = int(round(x[0]))   # Número de baterias em paralelo
        Np_uc = int(round(x[1]))  # Número de supercapacitores em paralelo

        # Cálculo do número total de componentes
        total_baterias = Np_b * Nm_b * Ns_b
        total_supercaps = Np_uc * Nm_uc * Ns_uc

        # Cálculo do custo inicial (investimento)
        custo_inicial = (total_baterias * Pb + total_supercaps * Puc)

        # Simulação para calcular energia rejeitada
        cache_key = (Np_b, Np_uc)
        if cache_key not in self.simulation_cache:
            sim = Simulation()
            sim.setParam_Batt(C=Cap_b, Ns=Ns_b, Np=Np_b, Nm=Nm_b, Vnom=3.2, SoC=50, T_m = T_xb)
            sim.setParam_UC(C=3400, Ns=Ns_uc, Np=Np_uc, Nm=Nm_uc, Vnom=3, SoC=50, T_m=T_xuc)
            data = r"data\CR-3112_28-09-24_AGGREGATED.xlsx"
            sheet = "Log"
            sim.simulate(data, sheet, threshold=1000)
            energia_rejeitada = sum(sim._p_reject) / 3600  # Wh
            # Energia absorvida é a soma das potências negativas (absorvidas) pelos sistemas
            p_batt_arr = np.array(sim._p_batt)
            p_uc_arr = np.array(sim._p_uc)
            energia_absorvida = (
                np.abs(np.sum(p_batt_arr[p_batt_arr < 0])) +
                np.abs(np.sum(p_uc_arr[p_uc_arr < 0]))
            ) / 3600  # Wh
            self.simulation_cache[cache_key] = (energia_rejeitada, energia_absorvida)
        else:
            energia_rejeitada, energia_absorvida = self.simulation_cache[cache_key]

        # Energia absorvida por ciclo (Wh)
        energia_absorvida_ciclo = energia_absorvida
        print(f"Energia absorvida por ciclo (Np_b: {Np_b}, Np_uc: {Np_uc}): {energia_absorvida_ciclo} Wh")
        # Número de ciclos por dia e por mês
        horas_operacao_dia = 24 * taxa_disponibilidade
        ciclos_por_dia = horas_operacao_dia / duracao_ciclo_horas
        self.ciclos_por_mes = ciclos_por_dia * dias_por_mes

        # Energia absorvida por mês (Wh -> kWh)
        energia_absorvida_mes_kWh = (energia_absorvida_ciclo * self.ciclos_por_mes) / 1000

        # Economia mensal de diesel
        litros_diesel_economizados = energia_absorvida_mes_kWh / rendimento_diesel
        economia_mensal = litros_diesel_economizados * preco_diesel

        # Vida útil dos componentes em meses
        vida_util_bateria_meses = ciclos_bateria_vida / self.ciclos_por_mes if self.ciclos_por_mes > 0 else horizonte_analise_meses
        vida_util_supercap_meses = horas_supercap_vida / (horas_operacao_dia * dias_por_mes) if horas_operacao_dia > 0 else horizonte_analise_meses

        # Fluxo de caixa mensal
        fluxo_caixa = []
        mes = 0
        custo_bateria = total_baterias * Pb
        custo_supercap = total_supercaps * Puc
        proximo_reinv_bat = vida_util_bateria_meses                                # Essa parte não funciona direito ainda, deveria ser o calculo de quando a bateria deveria ser trocada
        proximo_reinv_uc = vida_util_supercap_meses                                # Essa parte não funciona direito ainda, deveria ser o calculo de quando o supercapacitor deveria ser trocado
        while mes < horizonte_analise_meses:
            if mes == 0:
                fluxo_caixa.append(-custo_inicial)  # Investimento inicial
            else:
                # Substituição de bateria
                if abs(mes - proximo_reinv_bat) < 1e-6:
                    fluxo_caixa.append(-custo_bateria)
                    proximo_reinv_bat += vida_util_bateria_meses
                # Substituição de supercap
                elif abs(mes - proximo_reinv_uc) < 1e-6:
                    fluxo_caixa.append(-custo_supercap)
                    proximo_reinv_uc += vida_util_supercap_meses
                else:
                    fluxo_caixa.append(economia_mensal)
            mes += 1

        # Cálculo do VPL
        vpl = 0
        for i, fc in enumerate(fluxo_caixa):
            vpl += fc / ((1 + taxa_desconto_mensal) ** i)

        print(f"VPL (Np_b: {Np_b}, Np_uc: {Np_uc}): {vpl}")
        print(f'---------------------------------------------------------')

        # Como a otimização é de minimização, usamos o valor negativo do VPL
        out["F"] = [-vpl]
        out["G"] = []
        
        # Armazenar o fluxo de caixa se for a melhor solução até agora
        if not hasattr(self, 'melhor_vpl') or vpl > self.melhor_vpl:
            self.melhor_vpl = vpl
            self.melhor_fluxo_caixa = fluxo_caixa.copy()

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Otimização ------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

problem = MyProblem()

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM

algorithm = NSGA2(
    pop_size=50,
    n_offsprings=25,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=15),
    mutation=PM(eta=15, prob=0.2),
    eliminate_duplicates=True
)

from pymoo.termination import get_termination

termination = get_termination("n_gen", 20)

from pymoo.optimize import minimize

res = minimize(problem,
               algorithm,
               termination,
               seed=1,
               save_history=True,
               verbose=True)

# Após a otimização
X = res.X
F = res.F

print(f'X: {X}')
print(f'F: {F}')

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Visualização do espaço de design -------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

plt.figure(figsize=(7, 5))
X_int = np.round(X).astype(int)
plt.scatter(X_int[:, 0], X_int[:, 1], s=30, facecolors='r', edgecolors='r', zorder=3)
plt.xlabel('Número de Baterias em Paralelo')
plt.ylabel('Número de Supercapacitores em Paralelo')
plt.title("Espaço de Design")
plt.grid(zorder=1)
plt.xticks(np.arange(1, 11, 1))
plt.yticks(np.arange(1, 11, 1))
plt.xlim(problem.xl[0]-1, problem.xu[0]+1)
plt.ylim(problem.xl[1]-1, problem.xu[1]+1)

# Imprimir resultados
print("\nResultados da Otimização:")
print("------------------------")
for i in range(min(10, len(X))):  # Mostrar as 10 melhores soluções
    print(f"\nSolução {i+1}:")
    print(f"Número de baterias em paralelo: {int(round(X[i,0]))}")
    print(f"Número de supercapacitores em paralelo: {int(round(X[i,1]))}")
    print(f"VPL (Valor Presente Líquido): R$ {(-F[i,0]):,.2f}")

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Seleção da melhor solução ------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

idx_best = np.argmin(F[:, 0])  # Menor valor negativo de F => maior VPL
best_Np_b = int(round(X[idx_best, 0]))
best_Np_uc = int(round(X[idx_best, 1]))

# Rodar a simulação para a melhor solução
sim = Simulation()
sim.setParam_Batt(C=Cap_b, Ns=Ns_b, Np=best_Np_b, Nm=Nm_b, Vnom=3.2, SoC=50, T_m=T_xb)
sim.setParam_UC(C=3400, Ns=Ns_uc, Np=best_Np_uc, Nm=Nm_uc, Vnom=3, SoC=50, T_m=T_xuc)
data = r"data\CR-3112_28-09-24_AGGREGATED.xlsx"
sheet = "Log"

# Carregar dados do Excel para plotar potência, corrente e tensão de entrada
import pandas as pd
input_df = pd.read_excel(data, sheet_name="Log")

time = np.arange(len(input_df))

# Potência do diesel (entrada real do sistema)
powers_diesel = input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"]  # em Watts

# Ajustar a simulação para usar a potência do diesel como entrada
sim.simulate_custom_powers(powers_diesel)

# O restante do código permanece igual, usando os resultados da simulação

# Carregar dados do Excel para plotar potência, corrente e tensão de entrada
import pandas as pd
input_df = pd.read_excel(data, sheet_name="Log")

time = np.arange(len(input_df))

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Potência, Corrente e Tensão de Entrada -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------  

fig, axs = plt.subplots(3, 1, figsize=(12, 6), sharex=True)
axs[0].plot(time, input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"]/1000, label='Potência [kW]')
axs[0].set_ylabel('Potência [kW]')
axs[0].grid()
axs[0].legend(loc="upper right")
axs[0].set_title('Dados de Entrada do Ciclo (Arquivo Excel)')

axs[1].plot(time, input_df['fa08_m2amps'], label='Corrente [A]', color='orange')
axs[1].set_ylabel('Corrente [A]')
axs[1].grid()
axs[1].legend(loc='upper right')

axs[2].plot(time, input_df['fa00_altoutvolts'], label='Tensão [V]', color='green')
axs[2].set_ylabel('Tensão [V]')
axs[2].set_xlabel('Tempo [s]')
axs[2].set_xlim(0, len(input_df))
axs[2].grid()
axs[2].legend(loc='upper right')

plt.tight_layout()
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Potência e Corrente usando subplots -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

sim_time = np.arange(len(sim._p_batt))
fig, axs = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

# Potência em kW
p_batt_kw = np.array(sim._p_batt) / 1e3
p_uc_kw = np.array(sim._p_uc) / 1e3

color_batt = 'tab:blue'
color_uc = 'tab:blue'
color_batt_i = 'tab:orange'
color_uc_i = 'tab:orange'

# --- BATERIA ---
axs[0].set_ylabel('Potência Bateria [kW]', color=color_batt)
l1 = axs[0].plot(sim_time, p_batt_kw, label='Potência Bateria [kW]', color=color_batt)
l_bat_rej = axs[0].plot(sim_time, np.array(sim._p_bat_reject), label='Potência Rejeitada Bateria [kW]', color='tab:red', linestyle=':')
axs[0].tick_params(axis='y', labelcolor=color_batt)

ax2_0 = axs[0].twinx()
l2 = ax2_0.plot(sim_time, sim._i_bat, label='Corrente Bateria [A]', color=color_batt_i)
ax2_0.set_ylabel('Corrente Bateria [A]', color=color_batt_i)
ax2_0.tick_params(axis='y', labelcolor=color_batt_i)

lns0 = l1 + l_bat_rej + l2
labs0 = [l.get_label() for l in lns0]
axs[0].legend(lns0, labs0, loc='upper right')
axs[0].set_title('Bateria')
axs[0].grid()

# --- SUPERCAPACITOR ---
axs[1].set_ylabel('Potência Supercapacitor [kW]', color=color_uc)
l3 = axs[1].plot(sim_time, p_uc_kw, label='Potência Supercapacitor [kW]', color=color_uc)
l_uc_rej = axs[1].plot(sim_time, np.array(sim._p_uc_reject), label='Potência Rejeitada Supercapacitor [kW]', color='tab:purple', linestyle=':')
axs[1].tick_params(axis='y', labelcolor=color_uc)

ax2_1 = axs[1].twinx()
l4 = ax2_1.plot(sim_time, sim._i_uc, label='Corrente Supercapacitor [A]', color=color_uc_i)
ax2_1.set_ylabel('Corrente Supercapacitor [A]', color=color_uc_i)
ax2_1.tick_params(axis='y', labelcolor=color_uc_i)

lns1 = l3 + l_uc_rej + l4
labs1 = [l.get_label() for l in lns1]
axs[1].legend(lns1, labs1, loc='upper right')
axs[1].set_title('Supercapacitor')
axs[1].grid()

# --- POTÊNCIA REJEITADA TOTAL ---
p_rej_total = np.array(sim._p_bat_reject) + np.array(sim._p_uc_reject)
axs[2].plot(sim_time, p_rej_total, label='Potência Rejeitada Total [kW]', color='tab:orange')
axs[2].set_ylabel('Potência Rejeitada Total [kW]')
axs[2].set_xlabel('Amostra')
axs[2].legend(loc='upper right')
axs[2].set_title('Potência Rejeitada Total')
axs[2].grid()

plt.tight_layout()
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico SoC, Tensão e Corrente: Bateria x Supercapacitor -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

fig, axs = plt.subplots(3, 2, figsize=(14, 8), sharex=True)

# Linha 1: SoC
axs[0, 0].plot(sim_time, sim._SoC, color='tab:blue', label='SoC Bateria')
axs[0, 0].set_ylabel('SoC Bateria [%]')
axs[0, 0].legend(loc='upper right')
axs[0, 0].grid()

axs[0, 1].plot(sim_time, sim._SoC_UC, color='tab:blue', label='SoC Supercapacitor')
axs[0, 1].set_ylabel('SoC UC [%]')
axs[0, 1].legend(loc='upper right')
axs[0, 1].grid()

# Linha 2: Tensão
axs[1, 0].plot(sim_time, sim._v_banco_bat, color='tab:orange', label='Tensão Bateria')
axs[1, 0].set_ylabel('Tensão Bateria [V]')
axs[1, 0].legend(loc='upper right')
axs[1, 0].grid()

axs[1, 1].plot(sim_time, sim._v_banco_uc, color='tab:orange', label='Tensão Supercapacitor')
axs[1, 1].set_ylabel('Tensão UC [V]')
axs[1, 1].legend(loc='upper right')
axs[1, 1].grid()

# Linha 3: Corrente
axs[2, 0].plot(sim_time, sim._i_bat, color='tab:green', label='Corrente Bateria')
axs[2, 0].set_ylabel('Corrente Bateria [A]')
axs[2, 0].set_xlabel('Amostra')
axs[2, 0].legend(loc='upper right')
axs[2, 0].grid()

axs[2, 1].plot(sim_time, sim._i_uc, color='tab:green', label='Corrente Supercapacitor')
axs[2, 1].set_ylabel('Corrente UC [A]')
axs[2, 1].set_xlabel('Amostra')
axs[2, 1].legend(loc='upper right')
axs[2, 1].grid()

plt.suptitle('SoC, Tensão e Corrente: Bateria (esq.) x Supercapacitor (dir.)')
plt.tight_layout(rect=[0, 0.03, 1, 0.97])
plt.show(block=False)

plt.figure(figsize=(12, 4))

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- Comparação entre a potência do diesel e a gerenciada ------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

# Potência medida do sistema (entrada)
pot_sistema = input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"] / 1000  # kW
plt.plot(time, pot_sistema, label='Potência Sistema (Diesel) [kW]', color='black')

# Soma das potências simuladas (bateria + supercapacitor + rejeitada)
pot_simulada = (np.array(sim._p_batt) + np.array(sim._p_uc) + np.array(p_rej_total) * 1000) / 1e3  # kW
pot_simulada_2 = (np.array(sim._p_batt) + np.array(sim._p_uc)) / 1e3  # kW
plt.plot(sim_time, pot_simulada, label='Potência Administrada Total [kW]', color='tab:blue', linestyle='--')
plt.plot(sim_time, pot_simulada_2, label='Potência Bateria + Supercapacitor [kW]', color='tab:red', linestyle='--')

plt.ylabel('Potência [kW]')
plt.xlabel('Amostra')
plt.title('Comparação: Potência do Sistema vs. Simulação')
plt.legend(loc='upper right')
plt.grid()
plt.tight_layout()
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Fluxo de Caixa Mensal (usando cashflow) -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

import cashflow

# Usar o fluxo de caixa da melhor solução já calculado durante a otimização
if hasattr(problem, 'melhor_fluxo_caixa'):
    cf = cashflow.CashFlow(problem.melhor_fluxo_caixa)
    cf.plot()
    # plt.title('Fluxo de Caixa Mensal - Melhor Solução')
    # plt.xlabel('Meses')
    # plt.ylabel('Fluxo de Caixa (USD)')
    # plt.show(block=True)
else:
    print("Aviso: Fluxo de caixa da melhor solução não encontrado.")

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Degradação da Bateria ----------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------
horas_operacao_dia = 24 * taxa_disponibilidade
ciclos_por_dia = horas_operacao_dia / duracao_ciclo_horas
ciclos_por_mes = ciclos_por_dia * dias_por_mes
capacidade_bateria = np.ones(horizonte_analise_meses)                       # Cria um vetor para análisar mes a mes a saude da bateria
for i in range(horizonte_analise_meses):
    porcentagem_de_ciclos = (i * ciclos_por_mes) / ciclos_bateria_vida                                        
    if porcentagem_de_ciclos <= 1:
        capacidade_bateria[i] = 1 - 0.2 * porcentagem_de_ciclos                               # Linear até 80%
    else:
        capacidade_bateria[i] = 0.8  # Após vida útil, mantém 80%
plt.figure(figsize=(10, 4))
plt.plot(np.arange(horizonte_analise_meses), capacidade_bateria * 100)
plt.title('Degradação da Bateria ao Longo do Tempo')
plt.xlabel('Meses')
plt.ylabel('Capacidade Residual (%)')
plt.ylim(75, 105)
plt.grid()
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Degradação do Supercapacitor ------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------
horas_operacao_mes = 24 * taxa_disponibilidade * dias_por_mes
capacidade_supercap = np.ones(horizonte_analise_meses)
for i in range(horizonte_analise_meses):
    horas = 100 - 100*((i * horas_operacao_mes) / horas_supercap_vida)
    if horas <= 0:
        capacidade_supercap[i] = 0
    else:
        capacidade_supercap[i] = horas
print(capacidade_supercap)
plt.figure(figsize=(10, 4))
plt.plot(np.arange(horizonte_analise_meses), capacidade_supercap, color='orange')
plt.title('Degradação do Supercapacitor ao Longo do Tempo')
plt.xlabel('Meses')
plt.ylabel('Capacidade Residual (%)')
plt.ylim(75, 105)
plt.grid()
plt.show(block=True)

# # ----------------------------------------------------------------------------------------------------------------------------------------------------
# # ----------------------------------------------- Gráfico de Potência e Corrente usando subplots -------------------------------------------------
# # ----------------------------------------------------------------------------------------------------------------------------------------------------

# fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# # Potência em kW
# p_batt_kw = np.array(sim._p_batt) / 1e3
# p_uc_kw = np.array(sim._p_uc) / 1e3

# color_batt_p = 'tab:blue'
# color_batt_i = 'tab:green'
# color_uc_p = 'tab:red'
# color_uc_i = 'tab:orange'

# # --- BATERIA ---
# ax1.set_ylabel('Potência Bateria (kW)', color=color_batt_p)
# l1 = ax1.plot(sim_time, p_batt_kw, label='Potência Bateria (kW)', color=color_batt_p)
# ax1.tick_params(axis='y', labelcolor=color_batt_p)

# ax1b = ax1.twinx()
# ax1b.set_ylabel('Corrente Bateria (A)', color=color_batt_i)
# l2 = ax1b.plot(sim_time, sim._i_bat, label='Corrente Bateria (A)', color=color_batt_i, linestyle='--')
# ax1b.tick_params(axis='y', labelcolor=color_batt_i)

# # Legenda combinada
# lns1 = l1 + l2
# labs1 = [l.get_label() for l in lns1]
# ax1.legend(lns1, labs1, loc='upper right')
# ax1.set_title('Bateria')

# # --- SUPERCAPACITOR ---
# ax2.set_ylabel('Potência Supercapacitor (kW)', color=color_uc_p)
# l3 = ax2.plot(sim_time, p_uc_kw, label='Potência Supercapacitor (kW)', color=color_uc_p)
# ax2.tick_params(axis='y', labelcolor=color_uc_p)

# ax2b = ax2.twinx()
# ax2b.set_ylabel('Corrente Supercapacitor (A)', color=color_uc_i)
# l4 = ax2b.plot(sim_time, sim._i_uc, label='Corrente Supercapacitor (A)', color=color_uc_i, linestyle='--')
# ax2b.tick_params(axis='y', labelcolor=color_uc_i)

# # Legenda combinada
# lns2 = l3 + l4
# labs2 = [l.get_label() for l in lns2]
# ax2.legend(lns2, labs2, loc='upper right')
# ax2.set_title('Supercapacitor')

# plt.xlabel('Amostra')
# plt.tight_layout()
# plt.show(block=True)


