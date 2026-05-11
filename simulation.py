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
        # Modo atual da histerese do supercapacitor em relação à bateria
        # "idle"      : sem troca de potência apenas pela histerese
        # "charge_uc" : bateria carregando o supercapacitor
        # "discharge_uc" : supercapacitor descarregando para a bateria
        self._uc_hyst_mode = "idle"
        # Contador: segundos em idle com SoC > upper e sem demanda (após N s permite descarga)
        self._idle_upper_nodemand_s = 0
        # True se entramos em discharge_uc sem demanda; não interromper até lower_limit
        self._discharge_started_by_timer = False
        self._uc_diff = []

    def configFluxUC2Bat(self, SoC_uc_ref : float, BH : float, Taxa : int) -> None:
        """
        Configura a histerese do sistema.\n
        :param float SoC_uc_ref: Setpoint para o estado de carga do supercapacitor. \\n
        :param float BH: Banda de histerese, em SoC, para o supercapacitor.  \n
        :param int Taxa: Taxa (1~8C) na qual o SC descarrega na bateria. \n
        """
        self._SoC_uc_ref = SoC_uc_ref
        self._BH = BH
        self._Taxa_ref = Taxa
        # 2) Controle de histerese entre bateria e supercapacitor
        self.upper_limit = self._SoC_uc_ref + self._BH
        self.lower_limit = self._SoC_uc_ref - self._BH
        self._hysteresis_flag = 0
        self._uc_hyst_mode_vector = []

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

    def plot_results(self):
        """Plota resultados da simulação"""
        fig, axs = plt.subplots(3, 2, figsize=(self.fig_width_cm*2, self.fig_height_cm), sharex=True)
        time = np.arange(len(self._SoC))
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
        
        self._idle_upper_nodemand_s = 0
        self._discharge_started_by_timer = False
        # Simulação
        for i, power in enumerate(powers):
            power_bat, power_uc = self.supervisory_control(power, threshold, step_index=i, total_steps=len(powers))
            
            # Atualiza bateria
            i_bat, p_bat_reject_1 = self._batt.setCurrent(power_bat)
            SoC, v_banco_bat, p_bat_reject_2, i_bat, p_batt_actual = self._batt.updateEnergy(i_bat, 1)
            p_bat_reject = p_bat_reject_1 + p_bat_reject_2
            
            # Atualiza supercapacitor
            i_uc, p_uc_reject_1 = self._uc.setCurrent(power_uc)
            SoC_uc, v_banco_uc, p_uc_reject_2, i_uc, p_uc_actual = self._uc.updateEnergy(i_uc, 1)
            p_uc_reject = p_uc_reject_1 + p_uc_reject_2

            # Fluxo entre os elementos armazenadores de potência
            if self._uc_params["Np"] == 0:
                p_bat_reject = p_bat_reject + p_uc_reject
                p_uc_reject = 0

            if self._batt_params["Np"] == 0:
                p_uc_reject = p_uc_reject + p_bat_reject
                p_bat_reject = 0

            p_reject = p_bat_reject + p_uc_reject

            if self._hysteresis_flag == 1 and self._uc._Np != 0:
                if self._uc_hyst_mode == "idle":
                    if SoC_uc >= self.upper_limit:
                        self._uc_hyst_mode = "discharge_uc"
                    elif SoC_uc <= self.lower_limit:
                        self._uc_hyst_mode = "charge_uc"

            
            # Armazena resultados (p_batt_actual e p_uc_actual em W para balanço exato com o barramento)
            self._SoC.append(SoC)
            self._p_batt.append(p_batt_actual)  # Potência efetivamente trocada no passo (W)
            self._v_banco_bat.append(v_banco_bat)
            self._i_bat.append(i_bat)
            self._p_bat_reject.append(p_bat_reject)

            self._SoC_UC.append(SoC_uc)
            self._p_uc.append(p_uc_actual)  # Potência efetivamente trocada no passo (W)
            self._i_uc.append(i_uc)
            self._v_banco_uc.append(v_banco_uc)
            self._p_uc_reject.append(p_uc_reject)

            self._p_reject.append(p_reject)

        # Plota resultados
        # print(self._SoC_UC)                                     # APAGAR DEPOIS
        # self.plot_results(data["Time"])
        

    def supervisory_control(self, power: float, threshold : float, step_index: int = None, total_steps: int = None) -> tuple[float, float]:
        """
        Estratégia de controle para distribuição de potência
        :param float power: Potência atual (kW)
        :param float threshold: Limiar de potência para distribuição (kW)
        :param step_index: Índice do passo (opcional; usado para descarga no final do perfil)
        :param total_steps: Total de passos (opcional)
        """
        # Estratégia: UC absorve potências de pico e a bateria gerencia o SoC do UC
        power = power * 1000          # Conversão para W
        threshold = threshold * 1000  # Conversão para W

        SoC_uc = self._uc.getSoC()

        # 1) Controle de pico de potência no barramento
        if abs(power) > threshold and self._uc._Np != 0:
            power_uc = power - threshold if power > 0 else power + threshold
            power_bat = threshold if power > 0 else -threshold
            self._hysteresis_flag = 1
            return power_bat, power_uc

        # Potência de transferência histerese (W): V * I com I = C*Np*Taxa (C-rate em 1/h)
        # Convenção barramento: power_bat/power_uc > 0 = fornece ao barramento, < 0 = recebe
        V_batt = self._batt.getVoltage()
        I_transfer = self._batt_params["C"] * self._batt_params["Np"] * self._Taxa_ref  # A
        diff = V_batt * I_transfer  # W

        # Atualiza ou mantém o modo atual da histerese
        if self._uc_hyst_mode == "charge_uc" and self._uc._Np != 0:
            if SoC_uc >= self.upper_limit:
                # fim do ciclo de carga
                self._uc_hyst_mode = "idle"
                self._hysteresis_flag = 0
            else:
                # continua carregando UC
                power_uc = -diff
                power_bat = power + diff
                self._uc_hyst_mode_vector.append("charge_uc")
                self._uc_diff.append(diff)
                return power_bat, power_uc

        elif self._uc_hyst_mode == "discharge_uc" and self._uc._Np != 0:
            if SoC_uc <= self.lower_limit:
                # fim do ciclo de descarga
                self._uc_hyst_mode = "idle"
                self._hysteresis_flag = 0
            else:
                # continua descarregando UC
                power_uc = diff
                power_bat = power - diff
                self._uc_hyst_mode_vector.append("discharge_uc")
                self._uc_diff.append(diff)
                return power_bat, power_uc

        # Se está em idle, não faz transferência
        self._uc_hyst_mode_vector.append("idle")
        power_uc = 0
        power_bat = power
        return power_bat, power_uc
            
    
    
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
        
if __name__ == "__main__":
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

    data = r"data\Perfil_Sintetico.xlsx"
    sheet = "Log"
    diretorio_figuras = "Figuras/Validador/"

    # --------------------------------------------------------------------------
    # ------------------------- Definições do problema -------------------------
    # --------------------------------------------------------------------------
    SoC_uc_ref = 50
    BH = 2
    Taxa = 0.5
    Pth = 1750

    params_batt = {
        "C"     :   40,
        "Ns"    :   16,
        "Np"    :   5,
        "Nm"    :   30,
        "Vnom"  :   3.25,
        "SoC"   :   50,
        "T_m"   :   6
    }

    params_uc = {
        "C"         :   3400, 
        "Cap_uc"    :   280, 
        "Ns"        :   16, 
        "Np"        :   3, 
        "Nm"        :   15, 
        "Vnom"      :   3, 
        "SoC"       :   50, 
        "T_m"       :   8
    }

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    sim = Simulation()
    sim.configFluxUC2Bat(SoC_uc_ref, BH, Taxa)
    sim.setParam_Batt(C     =   params_batt["C"], 
                      Ns    =   params_batt["Ns"], 
                      Np    =   params_batt["Np"], 
                      Nm    =   params_batt["Nm"], 
                      Vnom  =   params_batt["Vnom"], 
                      SoC   =   params_batt["SoC"], 
                      T_m   =   params_batt["T_m"])
    
    sim.setParam_UC(C       =   params_uc["C"], 
                    Cap_uc  =   params_uc["Cap_uc"], 
                    Ns      =   params_uc["Ns"], 
                    Np      =   params_uc["Np"], 
                    Nm      =   params_uc["Nm"], 
                    Vnom    =   params_uc["Vnom"], 
                    SoC     =   params_uc["SoC"], 
                    T_m     =   params_uc["T_m"])
    sim.simulate(data, sheet, Pth)


    fig_width_cm = 24/2.4
    fig_height_cm = 18/2.4
    # Carregar dados do Excel para plotar potência, corrente e tensão de entrada
    input_df = pd.read_excel(data, sheet_name="Log")

    time = np.arange(len(input_df))

    # Potência do diesel (entrada real do sistema)
    try:
        powers_diesel = input_df["fa08_m2amps"] * input_df["fa00_altoutvolts"]  # em Watts
        corrente = input_df["fa08_m2amps"]
        tensao = input_df["fa00_altoutvolts"]
    except:
        powers_diesel = input_df["ai_04_m2amps"] * input_df["ai_11_altoutvolts"]  # em Watts
        corrente = input_df["ai_04_m2amps"]
        tensao = tensao = input_df["ai_11_altoutvolts"]

    # powers_diesel = powers_diesel / 1000  # Conversão para kW

    # ----------------------------------------------------------------------------------------------------------------------------------------------------
    # ----------------------------------------------- Gráfico de Potência, Corrente e Tensão de Entrada -------------------------------------------------
    # ----------------------------------------------------------------------------------------------------------------------------------------------------  

    fig, axs = plt.subplots(3, 1, figsize=(fig_width_cm, fig_height_cm*1.2), sharex=True)
    axs[0].set_title('Dados do Perfil de Potência (Dados Sintético)')
    axs[0].plot(time, tensao, linewidth = 2, label='Tensão [V]', color='tab:blue')
    axs[0].set_ylabel('Tensão [V]')
    axs[0].grid()
    axs[0].legend(loc='upper right')

    axs[1].plot(time, corrente, linewidth = 2, label='Corrente [A]', color='tab:orange')
    axs[1].set_ylabel('Corrente [A]')
    axs[1].grid()
    axs[1].legend(loc='upper right')

    axs[2].plot(time, powers_diesel/1000, linewidth = 2, label='Potência [kW]', color = "tab:green")
    axs[2].set_ylabel('Potência [kW]')
    axs[2].set_xlabel('Tempo [s]')
    axs[2].set_xlim(0, len(input_df))
    axs[2].hlines([Pth, -Pth], time[0], time[-1], linestyle = "dashed", color = "tab:red")
    axs[2].text(107, Pth + 0.05, f"Limiar: {Pth} kW", ha='center', va='bottom', color='red')
    axs[2].text(111, -Pth - 530, f"Limiar: {-Pth} kW", ha='center', va='bottom', color='red')
    axs[2].grid()
    axs[2].legend(loc="upper right")


    plt.tight_layout()
    plt.savefig(diretorio_figuras + f"_02_power_current_voltage.pdf", bbox_inches='tight')
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

    plt.tight_layout()
    plt.savefig(diretorio_figuras + f"_03_power_current_voltage_subplots.pdf", bbox_inches='tight')    
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
    plt.savefig(diretorio_figuras + f"_04_soc_voltage_current.pdf", bbox_inches='tight')
    plt.show(block=False)



    # ----------------------------------------------------------------------------------------------------------------------------------------------------
    # ---------------------------------------------- Comparação entre a potência do diesel e a gerenciada ------------------------------------------------
    # ----------------------------------------------------------------------------------------------------------------------------------------------------
    plt.figure(figsize=(fig_width_cm, fig_height_cm/1.5))
    p_rej_total = np.array(sim._p_bat_reject) + np.array(sim._p_uc_reject)
    pot_simulada = (np.array(sim._p_batt) + np.array(sim._p_uc) + np.array(p_rej_total) * 1000) / 1e3  # kW
    pot_simulada_2 = (np.array(sim._p_batt) + np.array(sim._p_uc)) / 1e3  # kW
    plt.plot(time, powers_diesel / 1000, label='Potência Sistema (Diesel) [kW]', color='black')
    plt.plot(time, pot_simulada, label='Potência Administrada Total [kW]', color='tab:blue', linestyle='--')
    plt.plot(time, pot_simulada_2, label='Potência Bateria + Supercapacitor [kW]', color='tab:red', linestyle='--')
    plt.ylabel('Potência [kW]')
    plt.xlabel('Tempo [s]')
    plt.title('Comparação: Potência do Sistema vs. Simulação')
    plt.legend(loc='upper right')
    plt.grid()
    plt.xlim([0, time[-1]])
    plt.tight_layout()
    plt.savefig(diretorio_figuras + f"_05_power_comparison.pdf", bbox_inches='tight')
    plt.show(block=False)


    plt.figure(figsize=(fig_width_cm, fig_height_cm/1.5))
    plt.plot(sim._uc_hyst_mode_vector, linewidth = 2, color='tab:blue', label='Modo de Histerese')
    plt.ylabel('Modo de Histerese')
    plt.xlabel('Tempo [s]')
    plt.title('Modo de Histerese')
    plt.legend(loc='upper right')
    plt.grid()
    plt.xlim([0, time[-1]])
    plt.tight_layout()
    # plt.savefig(diretorio_figuras + f"_06_hysteresis_mode.pdf", bbox_inches='tight')
    plt.show(block=True)
