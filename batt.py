import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Batt():
    fig_width_cm = 24/2.4
    fig_height_cm = 18/2.4

    def __init__(self):
        """Inicializa uma bateria com valores padrão"""
        self._C = 40
        self._Ns = 16
        self._Np = 3
        self._Nm = 24
        self._Vnom = 3.25
        self._SoC = 50
        self._min_SoC = 10                                                                          # SoC mínimo permitido (%)
        self._max_SoC = 90                                                                          # SoC máximo permitido (%)
        self._v_cel = self.LUT(self._SoC)                                                           # Calcula v_cel usando o SoC inicial
        self._v_banco = self._v_cel * self._Ns * self._Nm
        self._total_energy = (self._Np * self._C) * (self._Ns * self._Nm * self._Vnom)              # Wh
        self._SoC_Energy = (self._SoC/100) * self._total_energy
        self._configure_plots()

    def _configure_plots(self):
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

    def setParams(self, C: float, Ns: int, Np: int, Nm: int, Vnom: float, SoC: float, T_m: int) -> None:
        """
        Configura os parâmetros da bateria
        :param float C: Taxa de descarga da bateria (Ah)
        :param int Ns: Número de baterias em série
        :param int Np: Número de baterias em paralelo
        :param int Nm: Número de módulos
        :param float Vnom: Tensão nominal por célula (V)
        :param float SoC: Estado de carga inicial da bateria (%)
        :param int T_m: Multiplicador da capacidade do banco
        :raises ValueError: Se os parâmetros forem inválidos
        """
        if any(x <= 0 for x in [C, Ns, Np, Nm, Vnom]):
            raise ValueError("Todos os parâmetros devem ser positivos")
        
        if not self._min_SoC <= SoC <= self._max_SoC:
            raise ValueError(f"SoC deve estar entre {self._min_SoC}% e {self._max_SoC}%")

        self._C = C
        self._Ns = Ns
        self._Np = Np
        self._Nm = Nm
        self._Vnom = Vnom
        self._SoC = SoC
        self._T_m = T_m
        self._v_cel = self.LUT(self._SoC)  # Calcula v_cel usando o SoC inicial
        self._v_banco = self._v_cel * self._Ns * self._Nm
        self._total_energy = (Np * C) * (Ns * Nm * Vnom)  # Wh
        self._SoC_Energy = (SoC/100) * self._total_energy

    def LUT(self, SoC: float) -> float:
        """
        Calcula a tensão da bateria de acordo com o SoC usando interpolação
        :param float SoC: Estado de carga da célula (%)
        :return float: Tensão correspondente (V)
        """
        try:
            df = pd.read_csv("data\\LUT_batt.csv", sep=";")
            df["SoC"] = 100 - df["SoC"]  # Inverte SoC para corresponder ao padrão de carga
            indice_proximo = (df['SoC'] - SoC).abs().idxmin()
            tensao = df.loc[indice_proximo, 'Tensao']
            return float(tensao)
        except Exception as e:
            print(f"Erro ao ler LUT: {e}")
            return self._Vnom  # Retorna tensão nominal em caso de erro
        

    def batteryHealth(self, cycles_used: int, maximum_cycles: int) -> float:
        """
        Calcula a saúde da bateria baseado no número de ciclos usados
        :param int cycles_used: Número de ciclos usados
        :param int maximum_cycles: Número máximo de ciclos antes da falha
        :return float: Saúde da bateria (%)
        """
        try:
            df = pd.read_csv("data\\LUT_saude_batt.csv", sep=";")
            indice_proximo = (df['Ciclos'] - (cycles_used % maximum_cycles)).abs().idxmin()
            health = df.loc[indice_proximo, 'Saude']
            print(f"Saúde da bateria: {indice_proximo} ; {health}%")
            return float(health)
        except Exception as e:
            print("Erro ao ler LUT de saúde da bateria:", e)
            return e
        
    def plotBatterySoCGraph(self):
        """
        Plota o gráfico de Tensão x SoC da bateria
        """
        try:
            df = pd.read_csv("data\\LUT_batt.csv", sep=";")
            df["SoC"] = 100 - df["SoC"]  # Inverte SoC para corresponder ao padrão de carga
            plt.figure(figsize=(self.fig_width_cm, self.fig_height_cm/1.5))
            plt.plot(df['SoC'], df['Tensao'], color = 'tab:blue', linewidth = 2, label = "Tensão da bateria")
            plt.grid()
            plt.xlim([0,100])
            # plt.ylim([2.5, 4.2])
            plt.xlabel(r"Estado de Carga [\%]")
            plt.ylabel("Tensão da célula [V]")
            plt.title("Curva característica da bateria")
            plt.tight_layout()
            plt.savefig("Figuras\\curva_soc_bateria.pdf", dpi=300, bbox_inches='tight')
            plt.show()
        except Exception as e:
            print("Erro ao plotar gráfico de SoC da bateria:", e)

    def plotBatteryHealthGraph(self):
        """
        Plota o gráfico de saúde da bateria
        """
        try:
            df = pd.read_csv("data\\LUT_saude_batt.csv", sep=";")
            df.sort_values(by='Ciclos', inplace=True)
            plt.figure(figsize=(self.fig_width_cm, self.fig_height_cm/1.5))
            plt.plot(df['Ciclos'], df['Saude'], color = 'tab:blue', linewidth = 2, label = "Saúde da bateria")
            plt.grid()
            plt.xlim([0,5300])
            plt.ylim([60, 100])
            plt.xlabel("Número de Ciclos")
            plt.ylabel(r"Saúde da bateria [\%]")
            plt.title("Saúde da bateria por ciclos")
            plt.tight_layout()
            plt.savefig("Figuras\\curva_degradacao_bateria.pdf", dpi=300, bbox_inches='tight')
            plt.show()
        except Exception as e:
            print("Erro ao plotar gráfico de saúde da bateria:", e)

    def Energy2SoC(self, energy: float) -> float:
        """
        Calcula o SoC da bateria baseado na energia armazenada
        :param float energy: Energia total armazenada (Wh)
        :return float: Estado de carga (%)
        """
        return (energy * 100) / self._total_energy

    def setCurrent(self, power: float) -> (float | float | int):
        """
        Calcula a corrente por célula baseada na potência requerida
        :param float power: Potência requerida (W)
        :return float i_sat: Corrente por célula (A)
        :return float p_reject: Potência rejeitada (kW)
        :return int flag: Flag de saturação de corrente
        """
        i = power / self._v_banco
        i_sat = np.clip(i, -1 * self._T_m * self._Np * self._C, self._T_m * self._Np * self._C)     # Limita corrente em ambas direções
        i_reject = i - i_sat                                                                        # Calcula corrente rejeitada
        p_reject = (i_reject * self._v_banco)/1000                                                  # Calcula potência rejeitada
        flag = 0                                                                                    # Verificação de saturação de corrente
        if i_reject != 0: flag = 1                                                                  # Se houver corrente rejeitada, flag = 1
        else: flag = 0                                                                              # Se não houver corrente rejeitada, flag = 0
        return i_sat, p_reject, flag

    def getTotalEnergy(self) -> float:
        """
        Retorna a energia total armazenada na bateria
        :return float: Energia total (Wh)
        """
        return self._total_energy

    # def batteryDegradation(self, horizonte_analise_meses: int, vida_util_bateria_ciclos: int, duracao_ciclo_horas: int, taxa_disponibilidade: float) -> float:
    #     """
    #     Calcula a degradação baseada no horizonte de analise (meses), 
    #     a vida util da bateria (ciclos), duração do ciclo de operação (horas) e a 
    #     taxa de disponibilidade (%)
    #     :param float horizonte_analise_meses: Horizonte de analise (meses)
    #     :param float vida_util_bateria_ciclos: Vida util da bateria (ciclos)
    #     :param float duracao_ciclo_horas: Duração do ciclo de operação (horas)
    #     :param float taxa_disponibilidade: Taxa de disponibilidade (%)
    #     :return float: Degradação da bateria (%)
    #     """
    #     horas_operacao_dia = 24 * taxa_disponibilidade
    #     ciclos_por_dia = horas_operacao_dia / duracao_ciclo_horas
        
    
    
    def updateEnergy(self, flag: int, current: float, power: float, dt: float) -> (float | float | float):
        """
        Atualiza a energia total da bateria usando contador de Coulomb
        :param int flag: Flag de saturação de corrente
        :param float current: Corrente da bateria (A, + carga, - descarga)
        :param float power: Potência à ser gerenciada pelo banco
        :param float dt: Intervalo de tempo (s)
        :return float SoC: SoC da bateria
        :return float v_banco: Tensão total do pack de bateria
        :return float p_reject: Potência rejeitada (kW)
        """
        # Calcula variação de energia
        if flag == 0:
            energy_variation = power * dt / 3600
        else:
            charge = -1 * current * dt / 3600  # Converte para horas
            energy_variation = self._v_banco * charge
        
        # Calcula nova energia
        new_energy = self._SoC_Energy + energy_variation
        
        # Limita energia entre mínimo e máximo
        clip_energy = np.clip(
            new_energy, 
            (self._min_SoC/100) * self._total_energy,
            (self._max_SoC/100) * self._total_energy
        )
        p_reject = ((new_energy - clip_energy) / dt) / 1000             # Potência rejeitada (kW)


        
        self._SoC_Energy = clip_energy
        self._SoC = self.Energy2SoC(clip_energy)
        self._v_banco = self._Ns * self._Nm * self.LUT(self._SoC)
        
        return self._SoC, self._v_banco, p_reject


if __name__ == "__main__":
    batt = Batt()
    batt.setParams(40, 16, 3, 24, 3.25, 50, 10)
    batt.plotBatterySoCGraph()
    batt.batteryHealth(2000, 5500)
    batt.plotBatteryHealthGraph()