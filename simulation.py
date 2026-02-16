import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from batt import Batt
from UC import Uc
from time import sleep
import tabulate

class Simulation():
    def __init__(self):
        """Método para calcular o fluxo de potência do caminhão."""
        self.fig_width_cm = 24/2.4
        self.fig_height_cm = 18/2.4

        self._dt = 1                # Periodo de amostragem do sinal (s)
        
        # Dados da bateria
        self._SoC = []
        self._p_batt = []
        self._v_banco_bat = []
        self._i_bat = []
        self._p_bat_reject = []

        # Dados do supercapacitor
        self._v_banco_uc = []
        self._p_uc = []
        self._i_uc = []
        self._SoC_UC = []
        self._p_uc_reject = []
        
        self._p_reject = []

        self._uc = Uc()
        self._batt = Batt()

        

    def setParam_Batt(self, C: float, Ns: int, Np: int, Nm: int, Vnom: float, SoC: float, T_m: int) -> None:
        """
        Configura parâmetros da bateria
        :param float C: Taxa de descarga da bateria (Ah)
        :param int Ns: Número de baterias em série
        :param int Np: Número de baterias em paralelo
        :param int Nm: Número de módulos
        :param float Vnom: Tensão nominal por célula (V)
        :param float SoC: Estado de carga inicial da bateria (%)
        :param int T_m: Multiplicador da capacidade do banco
        :raises ValueError: Se os parâmetros forem inválidos
        """
        self._batt_params = {
            'C': C,
            'Ns': Ns,
            'Np': Np,
            'Nm': Nm,
            'Vnom': Vnom,
            'SoC': SoC,
            'T_m': T_m
        }
        self._batt.setParams(C, Ns, Np, Nm, Vnom, SoC, T_m)

    def setParam_UC(self, C: float, Cap_uc: float, Ns: int, Np: int, Nm : int, Vnom: float, SoC: float, T_m: int) -> None:
        """Configura parâmetros do supercapacitor
        :param float C: Capacitância do supercapacitor (F)
        :param float Cap_uc: Capacidade do supercapacitor (Ah)
        :param int Ns: Número de supercapacitores em série
        :param int Np: Número de supercapacitores em paralelo
        :param int Nm: Número de módulos
        :param float Vnom: Tensão nominal do supercapacitor (V)
        :param float SoC: Estado de carga inicial do supercapacitor (%)
        :param int T_m: Multiplicador da capacidade do banco
        """
        self._uc_params = {
            'C': C,
            'Cap_uc': Cap_uc,
            'Ns': Ns,
            'Np': Np,
            'Nm': Nm,
            'Vnom': Vnom,
            'SoC': SoC,
            'T_m': T_m
        }
        self._uc.setParams(C, Cap_uc, Ns, Np, Nm, Vnom, SoC, T_m)

    def plot_power_distribution(self, data, powers):
        """Plota distribuição de potência"""
        fig, axs = plt.subplots(figsize=(self.fig_width_cm, self.fig_height_cm), nrows=3, ncols=1, sharex=True)
        
        axs[0].step(data["Time"], data["Traction Power"], where="post", linewidth=2, color="tab:blue", label="Tração")
        axs[0].grid()
        axs[0].legend(loc="upper right")
        axs[0].set_ylabel("Potência [kW]")

        axs[1].step(data["Time"], data["Braking Power"], where="post", linewidth=2, color="tab:orange", label="Frenagem")
        axs[1].grid()
        axs[1].legend(loc="upper right")
        axs[1].set_ylabel("Potência [kW]")

        axs[2].step(data["Time"], powers, where="post", linewidth=2, color="tab:green", label="Total")
        axs[2].grid()
        axs[2].set_ylabel("Potência [kW]")
        axs[2].legend(loc="upper right")
        axs[2].set_xlim(0, data["Time"].iloc[-1])
        
        plt.tight_layout()
        plt.show(block=False)

    def plot_LUT(self):
        """Plota LUT da bateria"""
        df = pd.read_csv("data\\LUT_batt.csv", sep=";")
        plt.figure(figsize=(self.fig_width_cm, self.fig_height_cm/2))
        plt.plot(100 - df["SoC"], df["Tensao"], color = 'tab:blue', linewidth = 2, label = "LUT Bateria")   
        plt.grid()
        plt.legend(loc="upper left")
        plt.ylabel("Tensão [V]")
        plt.xlabel("SoC [%]")
        plt.title("Curva SoC x Tensão da bateria")
        plt.xlim(0, 100)
        plt.show(block = False)

    def plot_results(self, time):
        """Plota resultados da simulação"""
        fig, axs = plt.subplots(3, 2, figsize=(self.fig_width_cm*2, self.fig_height_cm), sharex=True)
        
        # Bateria (coluna esquerda)
        axs[0,0].step(time, self._SoC, linewidth=2, color="tab:blue", label="SoC Bateria")
        axs[0,0].grid()
        axs[0,0].legend(loc="upper right")
        axs[0,0].set_ylabel("SoC [%]")

        axs[1,0].step(time, self._v_banco_bat, linewidth=2, color="tab:orange", label="Tensão Bateria")
        axs[1,0].grid()
        axs[1,0].legend(loc="upper right")
        axs[1,0].set_ylabel("Tensão [V]")

        axs[2,0].step(time, self._i_bat, linewidth=2, color="tab:green", label="Corrente Bateria")
        axs[2,0].grid()
        axs[2,0].legend(loc="upper right")
        axs[2,0].set_ylabel("Corrente [A]")
        axs[2,0].set_xlabel("Tempo [s]")
        axs[2,0].set_xlim(0, time.iloc[-1])
        
        # Supercapacitor (coluna direita)
        axs[0,1].step(time, self._SoC_UC, linewidth=2, color="tab:blue", label="SoC UC")
        axs[0,1].grid()
        axs[0,1].legend(loc="upper right")
        axs[0,1].set_ylabel("SoC [%]")

        axs[1,1].step(time, self._v_banco_uc, linewidth=2, color="tab:orange", label="Tensão UC")
        axs[1,1].grid()
        axs[1,1].legend(loc="upper right")
        axs[1,1].set_ylabel("Tensão [V]")

        axs[2,1].step(time, self._i_uc, linewidth=2, color="tab:green", label="Corrente UC")
        axs[2,1].grid()
        axs[2,1].legend(loc="upper right")
        axs[2,1].set_ylabel("Corrente [A]")
        axs[2,1].set_xlabel("Tempo [s]")
        axs[2,1].set_xlim(0, time.iloc[-1])
        
        plt.tight_layout()
        plt.show()

    def simulate(self, data: str, sheet: str, threshold : float) -> None:
        """Executa simulação
        :param str data: Caminho para arquivo de dados
        :param str sheet: Nome da planilha
        :param float threshold: Limiar de potência para distribuição (kW)
        """
        data = pd.read_excel(data, sheet_name=sheet)
        data["Time"] = range(0, len(data))
        if sheet == "Dados":            powers = data['Traction Power'] - data["Braking Power"]
        if sheet == "Log":
            try:
                powers = (data['fa00_altoutvolts'] * data['fa08_m2amps']) / 1000
            except:
                powers = (data['ai_11_altoutvolts'] * data['ai_04_m2amps']) / 1000
        
        # Simulação
        for power in powers:
            # Distribuição de potência
            # print(f'power: {power}')                                                      # Conferencia 04/02/2026 ; funcionamento geral antes de colocar no documento
            power_bat, power_uc = self.supervisory_control(power, threshold)
            # print(f"Setpoints   :power_bat: {power_bat}    ;   power_uc: {power_uc}")     # Conferencia 04/02/2026 ; funcionamento geral antes de colocar no documento
            
            # Atualiza bateria
            i_bat, p_bat_reject_1 = self._batt.setCurrent(power_bat)
            SoC, v_banco_bat, p_bat_reject_2, i_bat = self._batt.updateEnergy(i_bat, 1)
            p_bat_reject = p_bat_reject_1 + p_bat_reject_2
            
            # Atualiza supercapacitor
            i_uc, p_uc_reject_1 = self._uc.setCurrent(power_uc)
            SoC_uc, v_banco_uc, p_uc_reject_2, i_uc = self._uc.updateEnergy(i_uc, 1)
            p_uc_reject = p_uc_reject_1 + p_uc_reject_2

            if self._uc_params["Np"] == 0:
                p_bat_reject = p_bat_reject + p_uc_reject
                p_uc_reject = 0

            if self._batt_params["Np"] == 0:
                p_uc_reject = p_uc_reject + p_bat_reject
                p_bat_reject = 0

            p_reject = p_bat_reject + p_uc_reject
            
            # Armazena resultados
            self._SoC.append(SoC)
            self._p_batt.append(i_bat * v_banco_bat)  # Potência realmente fornecida pela bateria
            self._v_banco_bat.append(v_banco_bat)
            self._i_bat.append(i_bat)
            self._p_bat_reject.append(p_bat_reject)

            self._SoC_UC.append(SoC_uc)
            self._p_uc.append(i_uc * v_banco_uc)  # Potência realmente fornecida pelo supercapacitor
            self._i_uc.append(i_uc)
            self._v_banco_uc.append(v_banco_uc)
            self._p_uc_reject.append(p_uc_reject)

            self._p_reject.append(p_reject)

        # Plota resultados
        # print(self._SoC_UC)                                     # APAGAR DEPOIS
        # self.plot_results(data["Time"])

    def simulate_custom_powers(self, powers, threshold=1000):
        """Executa simulação usando um vetor de potência diretamente como entrada
        :param powers: vetor de potência (em Watts)
        :param threshold: limiar de potência para distribuição (W)
        """
        # Limpa resultados anteriores
        self._SoC = []
        self._p_batt = []
        self._v_banco_bat = []
        self._i_bat = []
        self._p_bat_reject = []
        self._v_banco_uc = []
        self._p_uc = []
        self._i_uc = []
        self._SoC_UC = []
        self._p_uc_reject = []
        self._p_reject = []

        # Simulação
        for power in powers:
            # Distribuição de potência
            power_bat, power_uc = self.supervisory_control(power / 1000, threshold)  # supervisory_control espera kW

            # Atualiza bateria
            i_bat, p_bat_reject_1, flag = self._batt.setCurrent(power_bat)
            SoC, v_banco_bat, p_bat_reject_2 = self._batt.updateEnergy(flag, i_bat, power_bat, self._dt)
            p_bat_reject = p_bat_reject_1 + p_bat_reject_2

            # Atualiza supercapacitor
            i_uc, p_uc_reject_1, flag = self._uc.setCurrent(power_uc)
            SoC_uc, v_banco_uc, p_uc_reject_2, i_uc = self._uc.updateEnergy(flag, i_uc, power_uc, self._dt)
            p_uc_reject = p_uc_reject_1 + p_uc_reject_2

            p_reject = p_bat_reject + p_uc_reject

            # Armazena resultados
            self._SoC.append(SoC)
            self._p_batt.append(i_bat * v_banco_bat)  # Potência realmente fornecida pela bateria
            self._v_banco_bat.append(v_banco_bat)
            self._i_bat.append(i_bat)
            self._p_bat_reject.append(p_bat_reject)

            self._SoC_UC.append(SoC_uc)
            self._p_uc.append(i_uc * v_banco_uc)  # Potência realmente fornecida pelo supercapacitor
            self._i_uc.append(i_uc)
            self._v_banco_uc.append(v_banco_uc)
            self._p_uc_reject.append(p_uc_reject)

            self._p_reject.append(p_reject)

    def supervisory_control(self, power: float, threshold : float) -> tuple[float, float]:
        """
        Estratégia de controle para distribuição de potência
        :param float power: Potência atual (kW)
        :param float threshold: Limiar de potência para distribuição (kW)
        """
        # Estratégia: UC absorve potências de pico
        power = power * 1000                                                        # Conversão para W
        threshold = threshold * 1000                                                # Conversão para W
        if abs(power) > threshold:                                                  
            power_uc = power - threshold if power > 0 else power + threshold
            power_bat = threshold if power > 0 else -threshold
        else:
            power_uc = 0
            power_bat = power
            
        return power_bat, power_uc
    
    # def size_energy_storage(self, data: pd.DataFrame, threshold: float, config_bat : dict, config_uc : dict) -> tuple[dict, dict]:
    #     """
    #     Dimensiona banco de baterias e supercapacitores baseado no limiar de potência
        
    #     :param pd.DataFrame data: DataFrame com dados de potência
    #     :param float threshold: Limiar de potência para distribuição (kW)
    #     :param float config_bat: Configuração de tensão desejada (número de celulas serie e modulos)
    #     :param float config_uc: Configuração de tensão desejada (número de UC serie e modulos)
    #     :return: Dicionários com parâmetros da bateria e supercapacitor
    #     """
    #     # Converte threshold para W
    #     threshold = threshold * 1000

    #     # DoD desejado
    #     DoD_b = 0.3
    #     DoD_UC = 0.6


    #     # Calcula potências
    #     powers = (data['Traction Power'] - data["Braking Power"]) * 1000  # Converte para W
        
    #     # Separa potências entre bateria e UC
    #     power_bat = powers.copy()
    #     power_uc = powers.copy()
        
    #     # Aplica threshold
    #     power_bat[powers > threshold] = threshold
    #     power_bat[powers < -threshold] = -threshold
    #     power_uc[abs(powers) <= threshold] = 0
    #     power_uc[powers > threshold] = powers[powers > threshold] - threshold
    #     power_uc[powers < -threshold] = powers[powers < -threshold] + threshold
        
    #     # Calcula energias acumuladas
    #     dt = 1  # intervalo de 1s
    #     energy_bat = np.cumsum(power_bat * dt / 3600)  # Wh
    #     energy_uc = np.cumsum(power_uc * dt / 3600)    # Wh
        
    #     # Encontra máximas energias acumuladas
    #     max_energy_bat = np.max(energy_bat) - np.min(energy_bat)
    #     max_energy_uc = np.max(energy_uc) - np.min(energy_uc)

    #     print(f'max_energy_bat: {max_energy_bat} Wh ;   max_energy_uc: {max_energy_uc} Wh')           
        
    #     # Aplicação fator de segurança
    #     n = 1
    #     max_energy_bat *= n
    #     max_energy_uc *= n


    #     # Dimensiona bateria
    #     Vnom_bat = 3.2  # V
    #     C_bat = 40       # Ah
    #     energy_cell_bat = Vnom_bat * C_bat  # Wh por célula
        
    #     # Número de células necessárias
    #     N_cells_bat = np.ceil(max_energy_bat / (DoD_b * energy_cell_bat))
        
    #     # Configura arranjo (otimização básica)
    #     Ns_bat = config_bat["Ns"]
    #     Nm_bat = config_bat["Nm"]
    #     Np_bat = np.ceil(N_cells_bat / (Ns_bat * Nm_bat))
        
        
    #     # Dimensiona supercapacitor
    #     Vnom_uc = 3   # V
    #     C_uc = 3140     # F
        
    #     # Energia máxima por célula UC (E = 1/2 * C * V²)
    #     #energy_cell_uc = 0.5 * C_uc * (Vnom_uc**2) / 3600  # Wh

    #     # Configura arranjo (otimização básica)
    #     Ns_uc = config_uc["Ns"]                 # Fixo por restrições de tensão
    #     Nm_uc = config_uc["Nm"]

    #     # Calculo para numero de celulas em paralelo
    #     C_t = 2 * ((max_energy_uc * 3600) / (DoD_UC * (Vnom_uc * Ns_uc * Nm_uc )**2)) # F
    #     Np_uc = np.ceil((C_t * Ns_uc * Nm_uc) / C_uc)

    #     if Np_uc == 0: # Condição para geração do sistema de UC
    #         Np_uc = 1
        
    #     # Número de células necessárias
    #     #N_cells_uc = np.ceil(max_energy_uc / energy_cell_uc)
        
        
    #     #Np_uc = np.ceil(N_cells_uc / (Ns_uc * Nm_uc))
        
        
    #     # Retorna parâmetros calculados
    #     battery_params = {
    #         'C': C_bat,
    #         'Ns': int(Ns_bat),
    #         'Np': int(Np_bat),
    #         'Nm': int(Nm_bat),
    #         'Vnom': Vnom_bat,
    #         'max_energy': max_energy_bat
    #     }
        
    #     uc_params = {
    #         'C': C_uc,
    #         'Ns': int(Ns_uc),
    #         'Np': int(Np_uc),
    #         'Nm': int(Nm_uc),
    #         'Vnom': Vnom_uc,
    #         'max_energy': max_energy_uc
    #     }

    #     self.plot_energy_profile(df, energy_bat, energy_uc)
        
    #     return battery_params, uc_params
    
    def plot_energy_profile(self,df, E_bat, E_uc):
        """Plota perfil de energia"""
        fig, axs = plt.subplots(figsize=(self.fig_width_cm, self.fig_height_cm), nrows=2, ncols=1, sharex=True)
        
        # Bateria
        axs[0].plot( E_bat, linewidth=2, color="tab:blue", label="Bateria")
        axs[0].grid()
        axs[0].legend(loc="upper right")
        axs[0].set_ylabel("SoC [%]")
        
        # Supercapacitor
        axs[1].plot(E_uc, linewidth=2, color="tab:orange", label="Supercapacitor")
        axs[1].grid()
        axs[1].legend(loc="upper right")
        axs[1].set_ylabel("SoC [%]")
        axs[1].set_xlabel("Tempo [s]")

        plt.tight_layout()
    
    def save_data(self, path: str, threshold: int) -> None:
        """
        Método para salvar os dados de simulação.
        :param str path: Caminho para salvar os dados
        :param int threshold: Limiar de potência para distribuição (kW)
        """
        nome = f"simulacao_{threshold}kW.pkl"
        data = {
            "Tempo"          : range(0, len(self._SoC)),
            "C_bat"          : self._batt_params['C'],
            "Ns_bat"         : self._batt_params['Ns'],
            "Np_bat"         : self._batt_params['Np'],
            "Nm_bat"         : self._batt_params['Nm'],
            "Vnom_bat"       : self._batt_params['Vnom'],
            "SoC_inicial_bat": self._batt_params['SoC'],
            'SoC_bat': self._SoC,
            'v_banco_bat': self._v_banco_bat,
            'i_bat': self._i_bat,
            'p_bat_reject': self._p_bat_reject,
            'C_uc': self._uc_params['C'],
            'Ns_uc': self._uc_params['Ns'],
            'Np_uc': self._uc_params['Np'],
            'Nm_uc': self._uc_params['Nm'],
            'Vnom_uc': self._uc_params['Vnom'],
            'SoC_inicial_uc': self._uc_params['SoC'],
            'SoC_UC': self._SoC_UC,
            'v_banco_uc': self._v_banco_uc,
            'i_uc': self._i_uc,
            'p_uc_reject': self._p_uc_reject,
            'p_reject': self._p_reject
        }
        
        df = pd.DataFrame(data)
        df.to_pickle(path + nome)

    def compared_table(self, threshold):
        """
        Método para comparar os resultados da simulação.
        :param int threshold: Limiar de potência para distribuição (kW)
        """
        tabela = tabulate.tabulate([["Limiar", threshold],
                                    ["Energia máxima bateria (Wh)", self._batt.getTotalEnergy()],
                                    ["Energia máxima supercapacitor (Wh)", self._uc.getTotalEnergy()],
                                    ["Potência Rejeitada", ]])