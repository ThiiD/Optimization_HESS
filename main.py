import numpy as np
import matplotlib.pyplot as plt
import os
from time import sleep
import pandas as pd

from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.config import Config
Config.warnings['not_compiled'] = False

from simulation import Simulation

DEBUG = 0

plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"], # Or other serif font
    "axes.labelsize": 18,
    "axes.labelweight": "bold",
    "font.size": 18,
    "legend.fontsize": 16,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
})

fig_width_cm = 24/2.4
fig_height_cm = 18/2.4

# Parâmetros financeiros e operacionais
preco_diesel = 6.00  # R$/litro
rendimento_diesel = 3.0  # kWh/litro

# Estimativa do preço da eletronica de potencia
total_elepot = 2000
preco_razao_elepot = 1000      # Razao R$/kW

taxa_disponibilidade = 0.8  # 80% de disponibilidade diária

dias_por_mes = 30  # Considerando 30 dias por mês

# Degradação dos componentes
ciclos_bateria_vida = 5300  # ciclos até 80% da capacidade (Baseado no datasheet da bateria)
horas_supercap_vida = 1000000  # horas até 80% da capacidade (Baseado no datasheet do supercapacitor)

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
Vuc = 0.496                 # Volume do supercapacitor em L (Fonte: data_sources.xlsx)

Wb = 1.060                  # Peso da bateria em kg (Fonte: data_sources.xlsx)
Wuc = 0.460                 # Peso do supercapacitor em kg (Fonte: data_sources.xlsx)

Ns_b = 16                   # Número de baterias em serie
Nm_b = 24                   # Número de módulos de baterias
Ns_uc = 16                  # Número de supercapacitores em serie
Nm_uc = 20                  # Número de módulos de supercapacitores

Cap_b = 40.0                # Capacidade da bateria em Ah
T_xb = 6                    # Multiplicador da capacidade da bateria
Cap_uc = 280.0              # Capacidade do supercapacitor em Ah
T_xuc = 8                   # Multiplicador da capacidade do supercapacitor


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
        super().__init__(n_var=3,  # Np_b, Np_uc e Pth
                         n_obj=1,   # VPL e Volume
                         n_ieq_constr=0,  # Sem restrições
                         xl=np.array([1, 1, 500]),  # Mínimo de 1 para cada elemento armazenador e 500 para potencia (500 kW)
                         xu=np.array([10, 10, 2000]),  # Máximo de 10 para elementos armazenados e 2000 para potência (2000 kW)
                         type_var=np.int64)  # Especificando que as variáveis são inteiros
        self.simulation_cache = {}

    def setData(self, data: str, sheet: str):
        self._data = data
        self._sheet = sheet
        df = pd.read_excel(data, sheet_name=sheet)
        self._duracao_ciclo_operacao_hora = len(df) * 1 /3600
        print(self._duracao_ciclo_operacao_hora)
        sleep(5)


    def _evaluate(self, x, out, *args, **kwargs):
        Np_b = int(round(x[0]))     # Número de baterias em paralelo
        Np_uc = int(round(x[1]))    # Número de supercapacitores em paralelo
        Pth = x[2]                  # Variavel relativa a potencia

        # Cálculo do número total de componentes
        total_baterias = Np_b * Nm_b * Ns_b
        total_supercaps = Np_uc * Nm_uc * Ns_uc

        # Cálculo do custo inicial (investimento)
        custo_inicial = (total_baterias * Pb) + (total_supercaps * Puc) + (total_elepot * preco_razao_elepot)

        # Simulação para calcular energia rejeitada
        cache_key = (Np_b, Np_uc, Pth)
        if cache_key not in self.simulation_cache:
            sim = Simulation()
            sim.setParam_Batt(C=Cap_b, Ns=Ns_b, Np=Np_b, Nm=Nm_b, Vnom=3.2, SoC=50, T_m = T_xb)
            sim.setParam_UC(C=3400, Cap_uc=Cap_uc, Ns=Ns_uc, Np=Np_uc, Nm=Nm_uc, Vnom=3, SoC=50, T_m=T_xuc)
            # data = r"data\CR-3112_28-09-24_AGGREGATED.xlsx"
            # sheet = "Log"
            sim.simulate(self._data, self._sheet, threshold=Pth)
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
        print(f"Energia absorvida por ciclo (Np_b: {Np_b}, Np_uc: {Np_uc}, Pth: {Pth}): {energia_absorvida_ciclo} Wh")
        # Número de ciclos por dia e por mês
        horas_operacao_dia = 24 * taxa_disponibilidade
        ciclos_por_dia = horas_operacao_dia / self._duracao_ciclo_operacao_hora
        self.ciclos_por_mes = ciclos_por_dia * dias_por_mes

        # Energia absorvida por mês (Wh -> kWh)
        energia_absorvida_mes_kWh = (energia_absorvida_ciclo * self.ciclos_por_mes) / 1000

        # Economia mensal de diesel
        litros_diesel_economizados = energia_absorvida_mes_kWh / rendimento_diesel
        economia_mensal = litros_diesel_economizados * preco_diesel

        # Vida útil dos componentes em meses
        vida_util_bateria_meses = ciclos_bateria_vida / self.ciclos_por_mes if self.ciclos_por_mes > 0 else horizonte_analise_meses
        vida_util_supercap_meses = horas_supercap_vida / (horas_operacao_dia * dias_por_mes) if horas_operacao_dia > 0 else horizonte_analise_meses

        # Fluxo de caixa mensal e variaveis
        fluxo_caixa = []
        saude_bat = []                     
        troca_bat = []                     
        saude_uc = []                      
        troca_uc = []                      
        mes = 0
        numero_ciclos_batt_total = 0
        custo_bateria = total_baterias * Pb
        custo_supercap = total_supercaps * Puc

        # Analise financeira mensal
        while mes < horizonte_analise_meses:
            balanco_mes = 0
            if mes == 0:
                fluxo_caixa.append(-custo_inicial)  # Investimento inicial
                saude_bat.append(1)                 # Saude da bateria em 100% no mes 0
                troca_bat.append(0)                 # Nao a troca da bateria no mes 0 (saida ja realizada no custo inicial)
                saude_uc.append(1)                  # Saude do UC em 100% no mes 0
                troca_uc.append(0)                  # Nao ha troca de UC no mes 0 (saida ja realizada no custo inicial)

            else:
                balanco_mes += economia_mensal

                # Verifica substituição da bateria
                try:
                    print(f'Max SoC: {max(sim._SoC)}        ;       Min SoC: {min(sim._SoC)}')
                except:
                    print(f"EXCEÇÃO: {sim._SoC}")
                    sleep(50)
                numero_ciclos_batt_total += round(((max(sim._SoC) - min(sim._SoC)) / 100) * self.ciclos_por_mes)        # Calcula o numero de ciclos totais já realizados.
                #numero_ciclos_batt += self.ciclos_por_mes                                                              # Considera cada ciclo de operação um ciclo completo pra bateria

                if (numero_ciclos_batt_total / ciclos_bateria_vida) % 1 - 1 > sum(troca_bat):                           # Necessário realizar a troca da bateria
                    saude_bat_mensal = sim._batt.batteryHealth(numero_ciclos_batt_total % ciclos_bateria_vida, ciclos_bateria_vida)
                    saude_bat.append(saude_bat_mensal)
                    troca_bat.append(1)
                    balanco_mes += -custo_bateria
                else:
                    saude_bat_mensal = sim._batt.batteryHealth(numero_ciclos_batt_total % ciclos_bateria_vida, ciclos_bateria_vida)
                    saude_bat.append(saude_bat_mensal)
                    troca_bat.append(0)

                # Verifica substituição do supercapacitor
                saude_uc_mensal = saude_uc[-1] - (0.2*self.ciclos_por_mes*self._duracao_ciclo_operacao_hora/horas_supercap_vida)
                if saude_uc_mensal <= 0.8:
                    saude_uc_mensal = 1
                    saude_uc.append(saude_uc_mensal)
                    troca_uc.append(1)
                    balanco_mes += -custo_supercap
                else:
                    saude_uc.append(saude_uc_mensal)
                    troca_uc.append(0)

        
                fluxo_caixa.append(balanco_mes)
            mes += 1

        # Cálculo do VPL
        vpl = 0
        for i, fc in enumerate(fluxo_caixa):
            vpl += fc / ((1 + taxa_desconto_mensal) ** i)

        print(f"VPL (Np_b: {Np_b}, Np_uc: {Np_uc}, Pth: {Pth}): {vpl}")
        print(f'---------------------------------------------------------')

        # Como a otimização é de minimização, usamos o valor negativo do VPL
        out["F"] = [-vpl]
        out["G"] = []
        
        # Armazenar o fluxo de caixa se for a melhor solução até agora
        if not hasattr(self, 'melhor_vpl') or vpl > self.melhor_vpl:
            self.melhor_vpl = vpl
            self.saude_bat = saude_bat
            self.saude_uc = saude_uc
            self.melhor_fluxo_caixa = fluxo_caixa.copy()

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Otimização ------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

problem = MyProblem()
arquivo = "CR-3112_28-09-24_AGGREGATED.xlsx"
diretorio_figuras = "Figuras/" + arquivo.split(".")[0]
os.makedirs(diretorio_figuras, exist_ok=True)
data = "data/" + arquivo
sheet = "Log"
problem.setData(data, sheet)

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM

algorithm = NSGA2(
    pop_size=20,
    n_offsprings=20,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=15),
    mutation=PM(eta=15, prob=0.2),
    eliminate_duplicates=True
)

from pymoo.termination import get_termination

termination = get_termination("n_gen", 10)

from pymoo.optimize import minimize

if DEBUG == 1:
    X = np.array([[1.67568827 , 2.00387028 , 2.42676082],
                  [2.45828371 , 2.16749542 , 2.29327055],
                  [2.48089061 , 2.00954174 , 2.29311394],
                  [1.68066717 , 2.00387028 , 2.42676082],
                  [2.3824625  , 1.72352808 , 2.00388331],
                  [2.46946474 , 2.01153336 , 2.3417322 ],
                  [1.80650082 , 2.16749542 , 2.28653366],
                  [2.42323793 , 1.71690139 , 1.68014845],
                  [2.46766855 , 2.01030525 , 2.2843379 ],
                  [2.48441901 , 1.71674928 , 1.67953821],
                  [1.66524314 , 2.15307047 , 2.28653366],
                  [2.41622185 , 2.03898575 , 2.27603183],
                  [2.46373699 , 2.00926662 , 2.29311394],
                  [2.42026014 , 2.27297904 , 2.29195702],
                  [1.72671404 , 2.07843162 , 2.27633423],
                  [2.4163137  , 2.01700668 , 2.29311394],
                  [2.36949422 , 2.07832437 , 2.2792785 ],
                  [2.47444365 , 2.01153336 , 2.3423704 ],
                  [2.41139047 , 1.73282528 , 1.68065134],
                  [1.6689999  , 2.16749542 , 2.42979231],
                  [2.4697575  , 1.73621974 , 2.34483868],
                  [2.46946455 , 2.01062817 , 2.28950294],
                  [1.66916977 , 2.16749542 , 2.28717186],
                  [2.46713047 , 2.01001253 , 2.29311394],
                  [2.46946439 , 2.0297654  , 2.43276159],
                  [2.46713047 , 2.01008903 , 2.29311394],
                  [2.46948572 , 2.07401983 , 2.29519769],
                  [1.68789503 , 2.15607932 , 1.67230267],
                  [2.41622185 , 2.03923487 , 1.6801506 ],
                  [2.48134673 , 2.01033768 , 2.28198642],
                  [2.48198928 , 1.73621974 , 2.29436782],
                  [1.65552358 , 2.28751669 , 2.29436782],
                  [2.41451112 , 2.07752873 , 2.29439125],
                  [2.48169737 , 2.01153336 , 2.29372633],
                  [2.46881361 , 2.00976048 , 2.34335867],
                  [2.49832873 , 2.07843162 , 2.27633423],
                  [1.65569346 , 2.28751669 , 2.29436782],
                  [1.70103911 , 2.31993647 , 1.66291752],
                  [2.46883301 , 2.00967934 , 2.29349918],
                  [2.48441901 , 1.71674928 , 1.6801506 ],
                  [1.63209465 , 1.74098441 , 2.28551734],
                  [2.46713047 , 2.01033815 , 1.69723271],
                  [1.6689999  , 2.16749542 , 2.28653366],
                  [2.46975665 , 1.73621974 , 2.2944346 ],
                  [1.66524314 , 2.16749542 , 2.29327055],
                  [2.46881427 , 2.02905398 , 2.34555423],
                  [2.46946474 , 2.01153336 , 2.3423704 ],
                  [1.6689999  , 2.16749542 , 2.28717186],
                  [2.47644084 , 2.29618761 , 2.29436782],
                  [2.46832116 , 1.83287873 , 2.28198642]])
    F = np.array([[-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403],
                  [-1035859.12159403]])
    problem.saude_bat = [1, 0.9565283018867925,
                         0.913056603773585,
                         0.8695849056603775,
                         0.82611320754717,
                         1,
                         0.9565283018867925,
                         0.913056603773585,
                         0.8695849056603775,
                         0.82611320754717,
                         1,
                         0.9565283018867925]
    problem.saude_uc = [1,
                        0.9998848,
                        0.9997696,
                        0.9996544,
                        0.9995392000000001,
                        0.9994240000000001,
                        0.9993088000000001,
                        0.9991936000000001,
                        0.9990784000000001,
                        0.9989632000000002,
                        0.9988480000000002,
                        0.9987328000000002]
    problem.melhor_fluxo_caixa = [-2431162.56,
                                  np.float64(340362.6297192742),
                                  np.float64(340362.6297192742),
                                  np.float64(340362.6297192742),
                                  np.float64(340362.6297192742),
                                  np.float64(100808.06971927418),
                                  np.float64(340362.6297192742),
                                  np.float64(340362.6297192742),
                                  np.float64(340362.6297192742),
                                  np.float64(340362.6297192742),
                                  np.float64(100808.06971927418),
                                  np.float64(340362.6297192742)]

else:
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

plt.figure(figsize=(fig_width_cm, fig_height_cm))
ax = plt.axes(projection='3d')
X_int = np.round(X).astype(int)
try:
    ax.scatter(X_int[:, 0], X_int[:, 1], X_int[:, 2], s=30, facecolors='r', edgecolors='r', zorder=3)
except Exception as e:
    ax.scatter(X_int[0], X_int[1], X_int[2], s=30, facecolors='r', edgecolors='r', zorder=3)
    print("Solução unica!")
ax.set_xlabel('Número de Baterias em Paralelo')
ax.set_ylabel('Número de Supercapacitores em Paralelo')
ax.set_zlabel("Potência de Limiar")
ax.set_title("Espaço de Design")
ax.grid(zorder=1)
ax.set_xticks(np.arange(1, 11, 1))
ax.set_yticks(np.arange(1, 11, 1))
ax.set_xlim(problem.xl[0]-1, problem.xu[0]+1)
ax.set_ylim(problem.xl[1]-1, problem.xu[1]+1)
ax.set_zlim(problem.xl[2]-100, problem.xu[2]+100)
plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_01_design_space.pdf", bbox_inches='tight')
plt.show(block=False)


# Imprimir resultados
print("\nResultados da Otimização:")
print("------------------------")
for i in range(min(10, len(X))):  # Mostrar as 10 melhores soluções
    print(f"\nSolução {i+1}:")
    try:
        print(f"Número de baterias em paralelo: {int(round(X[i,0]))}")
        print(f"Número de supercapacitores em paralelo: {int(round(X[i,1]))}")
        print(f"Valor limiar de potência: {int(round(X[i,2]))}")
        print(f"VPL (Valor Presente Líquido): R$ {(-F[i,0]):,.2f}")
    except:
        print(f"Número de baterias em paralelo: {int(round(X[0]))}")
        print(f"Número de supercapacitores em paralelo: {int(round(X[1]))}")
        print(f"Valor limiar de potência: {int(round(X[2]))}")
        print(f"VPL (Valor Presente Líquido): R$ {(-F[0]):,.2f}")

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Seleção da melhor solução ------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------
try:
    idx_best = np.argmin(F[:, 0])  # Menor valor negativo de F => maior VPL
    best_Np_b = int(round(X[idx_best, 0]))
    best_Np_uc = int(round(X[idx_best, 1]))
    best_Pth = X[idx_best, 2]
except:
    idx_best = np.argmin(F[0])  # Menor valor negativo de F => maior VPL
    best_Np_b = int(round(X[0]))
    best_Np_uc = int(round(X[1]))
    best_Pth = X[2]


# Rodar a simulação para a melhor solução
sim = Simulation()
sim.setParam_Batt(C=Cap_b, Ns=Ns_b, Np=best_Np_b, Nm=Nm_b, Vnom=3.2, SoC=50, T_m=T_xb)
sim.setParam_UC(C=3400, Cap_uc=Cap_uc, Ns=Ns_uc, Np=best_Np_uc, Nm=Nm_uc, Vnom=3, SoC=50, T_m=T_xuc)
# data = r"data\CR-3112_28-09-24_AGGREGATED.xlsx"
# sheet = "Log"

# Carregar dados do Excel para plotar potência, corrente e tensão de entrada
import pandas as pd
input_df = pd.read_excel(data, sheet_name="Log")

time = np.arange(len(input_df))

# Potência do diesel (entrada real do sistema)
powers_diesel = input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"]  # em Watts

# Ajustar a simulação para usar a potência do diesel como entrada
sim.simulate(data, sheet, best_Pth)

# O restante do código permanece igual, usando os resultados da simulação

# # Carregar dados do Excel para plotar potência, corrente e tensão de entrada
# import pandas as pd
# input_df = pd.read_excel(data, sheet_name="Log")

# time = np.arange(len(input_df))

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Potência, Corrente e Tensão de Entrada -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------  

fig, axs = plt.subplots(3, 1, figsize=(fig_width_cm, fig_height_cm*1.2), sharex=True)
axs[0].set_title('Dados de Entrada do Ciclo (Arquivo Excel)')
axs[0].plot(time, input_df['fa00_altoutvolts'], linewidth = 2, label='Tensão [V]', color='tab:blue')
axs[0].set_ylabel('Tensão [V]')
axs[0].grid()
axs[0].legend(loc='upper right')

axs[1].plot(time, input_df['fa08_m2amps'], linewidth = 2, label='Corrente [A]', color='tab:orange')
axs[1].set_ylabel('Corrente [A]')
axs[1].grid()
axs[1].legend(loc='upper right')

axs[2].plot(time, input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"]/1000, linewidth = 2, label='Potência [kW]', color = "tab:green")
axs[2].set_ylabel('Potência [kW]')
axs[2].set_xlabel('Tempo [s]')
axs[2].set_xlim(0, len(input_df))
axs[2].grid()
axs[2].legend(loc="upper right")


plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_02_power_current_voltage.pdf", bbox_inches='tight')
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Potência e Corrente usando subplots -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

sim_time = np.arange(len(sim._p_batt))
fig, axs = plt.subplots(3, 2, figsize=(fig_width_cm*1.5, fig_height_cm*1.2), sharex=True)

# Potência em kW
p_batt_kw = np.array(sim._p_batt) / 1e3
p_uc_kw = np.array(sim._p_uc) / 1e3

color_power = "tab:green" 
color_voltage = "tab:blue"
color_current = "tab:orange"
color_reject_power = "tab:red"
color_soc = "tab:purple"

# -------   bateria     -------------
axs[0, 0].set_title("Bateria")
axs[0, 0].plot(time, p_batt_kw, linewidth = 2, label='Potência Bateria', color=color_power)
axs[0, 0].legend(loc = 'upper right')
axs[0, 0].set_ylabel("Potência [kW]")
axs[0, 0].grid()

axs[1, 0].plot(time, sim._i_bat, linewidth = 2, label='Corrente Bateria', color=color_current)
axs[1, 0].legend(loc = 'upper right')
axs[1, 0].set_ylabel("Corrente [A]")
axs[1, 0].grid()

axs[2, 0].plot(time, np.array(sim._p_bat_reject), linewidth = 2, label='Potência Rejeitada Bateria [kW]', color=color_reject_power)
axs[2, 0].legend(loc = 'upper right')
axs[2, 0].set_ylabel("Potência")
axs[2, 0].set_xlabel("Tempo [s]")
axs[2, 0].grid()
axs[2, 0].set_xlim([0, sim_time[-1]])


# -------   supercapacitor     -------------
axs[0, 1].set_title("Supercapacitor")
axs[0, 1].plot(time, p_uc_kw, linewidth = 2, label='Potência Supercapacitor', color=color_power)
axs[0, 1].legend(loc = 'upper right')
axs[0, 1].grid()

axs[1, 1].plot(time, sim._i_uc, linewidth = 2, label='Corrente Supercapacitor', color=color_current)
axs[1, 1].legend(loc = 'upper right')
axs[1, 1].grid()

axs[2, 1].plot(time, np.array(sim._p_uc_reject), linewidth = 2, label='Potência Rejeitada Supercapacitor [kW]', color=color_reject_power)
axs[2, 1].legend(loc = 'upper right')
axs[2, 1].set_xlabel("Tempo [s]")
axs[2, 1].grid()
axs[2, 1].set_xlim([0, time[-1]])

# # --- BATERIA ---
# axs[0].set_ylabel('Potência Bateria [kW]', color=color_batt)
# l1 = axs[0].plot(sim_time, p_batt_kw, label='Potência Bateria [kW]', color=color_batt)
# l_bat_rej = axs[0].plot(sim_time, np.array(sim._p_bat_reject), label='Potência Rejeitada Bateria [kW]', color='tab:red', linestyle=':')
# axs[0].tick_params(axis='y', labelcolor=color_batt)

# ax2_0 = axs[0].twinx()
# l2 = ax2_0.plot(sim_time, sim._i_bat, label='Corrente Bateria [A]', color=color_batt_i)
# ax2_0.set_ylabel('Corrente Bateria [A]', color=color_batt_i)
# ax2_0.tick_params(axis='y', labelcolor=color_batt_i)

# lns0 = l1 + l_bat_rej + l2
# labs0 = [l.get_label() for l in lns0]
# axs[0].legend(lns0, labs0, loc='upper right')
# axs[0].set_title('Bateria')
# axs[0].grid()

# # --- SUPERCAPACITOR ---
# axs[1].set_ylabel('Potência Supercapacitor [kW]', color=color_uc)
# l3 = axs[1].plot(sim_time, p_uc_kw, label='Potência Supercapacitor [kW]', color=color_uc)
# l_uc_rej = axs[1].plot(sim_time, np.array(sim._p_uc_reject), label='Potência Rejeitada Supercapacitor [kW]', color='tab:purple', linestyle=':')
# axs[1].tick_params(axis='y', labelcolor=color_uc)

# ax2_1 = axs[1].twinx()
# l4 = ax2_1.plot(sim_time, sim._i_uc, label='Corrente Supercapacitor [A]', color=color_uc_i)
# ax2_1.set_ylabel('Corrente Supercapacitor [A]', color=color_uc_i)
# ax2_1.tick_params(axis='y', labelcolor=color_uc_i)

# lns1 = l3 + l_uc_rej + l4
# labs1 = [l.get_label() for l in lns1]
# axs[1].legend(lns1, labs1, loc='upper right')
# axs[1].set_title('Supercapacitor')
# axs[1].grid()

# # --- POTÊNCIA REJEITADA TOTAL ---

# axs[2].plot(sim_time, p_rej_total, label='Potência Rejeitada Total [kW]', color='tab:orange')
# axs[2].set_ylabel('Potência Rejeitada Total [kW]')
# axs[2].set_xlabel('Amostra')
# axs[2].legend(loc='upper right')
# axs[2].set_title('Potência Rejeitada Total')
# axs[2].grid()

plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_03_power_current_voltage_subplots.pdf", bbox_inches='tight')    
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico SoC, Tensão e Corrente: Bateria x Supercapacitor -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------

fig, axs = plt.subplots(3, 2, figsize=(fig_width_cm*1.5, fig_height_cm*1.2), sharex=True)

# Linha 1: SoC
axs[0, 0].plot(time, sim._SoC, linewidth = 2, color=color_soc, label='SoC Bateria')
axs[0, 0].set_ylabel(r'SoC [\%]')
axs[0, 0].legend(loc='upper right')
axs[0, 0].grid()

axs[0, 1].plot(time, sim._SoC_UC, linewidth = 2, color=color_soc, label='SoC Supercapacitor')
axs[0, 1].legend(loc='upper right')
axs[0, 1].grid()

# Linha 2: Tensão
axs[1, 0].plot(time, sim._v_banco_bat, linewidth = 2, color=color_voltage, label='Tensão Bateria')
axs[1, 0].set_ylabel('Tensão [V]')
axs[1, 0].legend(loc='upper right')
axs[1, 0].grid()

axs[1, 1].plot(time, sim._v_banco_uc, linewidth = 2, color=color_voltage, label='Tensão Supercapacitor')
axs[1, 1].legend(loc='upper right')
axs[1, 1].grid()

# Linha 3: Corrente
axs[2, 0].plot(time, sim._i_bat, linewidth = 2, color=color_current, label='Corrente Bateria')
axs[2, 0].set_ylabel('Corrente [A]')
axs[2, 0].set_xlabel('Tempo [s]')
axs[2, 0].legend(loc='upper right')
axs[2, 0].set_xlim([0, time[-1]])
axs[2, 0].grid()

axs[2, 1].plot(time, sim._i_uc, linewidth = 2, color=color_current, label='Corrente Supercapacitor')
axs[2, 1].set_xlabel('Tempo [s]')
axs[2, 1].legend(loc='upper right')
axs[2, 1].set_xlim([0, time[-1]])
axs[2, 1].grid()

plt.suptitle('SoC, Tensão e Corrente: Bateria (esq.) x Supercapacitor (dir.)')
plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_04_soc_voltage_current.pdf", bbox_inches='tight')
plt.show(block=False)



# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- Comparação entre a potência do diesel e a gerenciada ------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------
plt.figure(figsize=(fig_width_cm, fig_height_cm/1.5))
p_rej_total = np.array(sim._p_bat_reject) + np.array(sim._p_uc_reject)
# Potência medida do sistema (entrada)
pot_sistema = input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"] / 1000  # kW
plt.plot(time, pot_sistema, label='Potência Sistema (Diesel) [kW]', color='black')

# Soma das potências simuladas (bateria + supercapacitor + rejeitada)
pot_simulada = (np.array(sim._p_batt) + np.array(sim._p_uc) + np.array(p_rej_total) * 1000) / 1e3  # kW
pot_simulada_2 = (np.array(sim._p_batt) + np.array(sim._p_uc)) / 1e3  # kW
plt.plot(time, pot_simulada, label='Potência Administrada Total [kW]', color='tab:blue', linestyle='--')
plt.plot(time, pot_simulada_2, label='Potência Bateria + Supercapacitor [kW]', color='tab:red', linestyle='--')

plt.ylabel('Potência [kW]')
plt.xlabel('Tempo [s]')
plt.title('Comparação: Potência do Sistema vs. Simulação')
plt.legend(loc='upper right')
plt.grid()
plt.xlim([0, time[-1]])
plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_05_power_comparison.pdf", bbox_inches='tight')
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
    plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_06_cashflow.pdf", bbox_inches='tight')
else:
    print("Aviso: Fluxo de caixa da melhor solução não encontrado.")

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Degradação da Bateria ----------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------
# horas_operacao_dia = 24 * taxa_disponibilidade
# ciclos_por_dia = horas_operacao_dia / self._duracao_ciclo_operacao_hora
# ciclos_por_mes = ciclos_por_dia * dias_por_mes
# capacidade_bateria = np.ones(horizonte_analise_meses)                       # Cria um vetor para análisar mes a mes a saude da bateria
# print(f'horizonte_analise_meses: {horizonte_analise_meses}')
# for i in range(horizonte_analise_meses):
#     porcentagem_de_ciclos = (i * ciclos_por_mes) / ciclos_bateria_vida                                        
#     if porcentagem_de_ciclos <= 1:
#         capacidade_bateria[i] = 1 - 0.2 * porcentagem_de_ciclos                               # Linear até 80%
#     else:
#         capacidade_bateria[i] = 1  # Após vida útil, mantém 80%
plt.figure(figsize=(fig_width_cm, fig_height_cm/1.5))
plt.step(np.arange(horizonte_analise_meses), np.array(problem.saude_bat) * 100, where="post")
plt.title('Degradação da Bateria ao Longo do Tempo')
plt.xlabel('Meses')
plt.ylabel(r'Capacidade Residual [\%]')
plt.ylim(75, 105)
plt.xlim(0, horizonte_analise_meses)
plt.grid()
plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_07_battery_degradation.pdf", bbox_inches='tight')
plt.show(block=False)

# ----------------------------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------- Gráfico de Degradação do Supercapacitor ------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------
# horas_operacao_mes = 24 * taxa_disponibilidade * dias_por_mes
# capacidade_supercap = np.ones(horizonte_analise_meses)
# for i in range(horizonte_analise_meses):
#     horas = 100 - 100*((i * horas_operacao_mes) / horas_supercap_vida)
#     if horas <= 0:
#         capacidade_supercap[i] = 0
#     else:
#         capacidade_supercap[i] = horas
# print(capacidade_supercap)
plt.figure(figsize=(fig_width_cm, fig_height_cm/1.5))
plt.step(np.arange(horizonte_analise_meses), np.array(problem.saude_uc) * 100, color='tab:blue', where="post")
plt.title('Degradação do Supercapacitor ao Longo do Tempo')
plt.xlabel('Meses')
plt.ylabel(r'Capacidade Residual [\%]')
plt.ylim(99.8, 100.2)
plt.xlim(0, horizonte_analise_meses)
plt.grid()
plt.tight_layout()
plt.savefig(diretorio_figuras + "/" f"{arquivo.split(".")[0]}_08_supercapacitor_degradation.pdf", bbox_inches='tight')
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


