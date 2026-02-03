import pandas as pd
import numpy as np

class Batt():
    def __init__(self):
        """Inicializa uma bateria com valores padrão"""
        self._C = 40
        self._Ns = 16
        self._Np = 3
        self._Nm = 24
        self._Vnom = 3.25
        self._SoC = 50
        self._min_SoC = 20                                                                          # SoC mínimo permitido (%) - DoD 20%
        self._max_SoC = 80                                                                          # SoC máximo permitido (%) - DoD 20%
        self._v_cel = self.LUT(self._SoC)                                                           # Calcula v_cel usando o SoC inicial
        self._v_banco = self._v_cel * self._Ns * self._Nm
        self._total_energy = (self._Np * self._C) * (self._Ns * self._Nm * self._Vnom)              # Wh
        self._SoC_Energy = (self._SoC/100) * self._total_energy
        self._C_rate = 6  # Valor padrão para taxa C

    def setParams(self, C: float, Ns: int, Np: int, Nm: int, Vnom: float, SoC: float, C_rate: float = None, DoD: float = None) -> None:
        """
        Configura os parâmetros da bateria
        :param float C: Taxa de descarga da bateria (Ah)
        :param int Ns: Número de baterias em série
        :param int Np: Número de baterias em paralelo
        :param int Nm: Número de módulos
        :param float Vnom: Tensão nominal por célula (V)
        :param float SoC: Estado de carga inicial da bateria (%)
        :param float C_rate: Taxa C máxima permitida (opcional)
        :param float DoD: Depth of Discharge desejado (opcional, 0.0 a 1.0)
        :raises ValueError: Se os parâmetros forem inválidos
        """
        if any(x <= 0 for x in [C, Ns, Np, Nm, Vnom]):
            raise ValueError("Todos os parâmetros devem ser positivos")
        
        if not 0 <= SoC <= 100:
            raise ValueError("SoC deve estar entre 0% e 100%")

        self._C = C
        self._Ns = Ns
        self._Np = Np
        self._Nm = Nm
        self._Vnom = Vnom
        self._SoC = SoC
        self._v_cel = self.LUT(self._SoC)  # Calcula v_cel usando o SoC inicial
        self._v_banco = self._v_cel * self._Ns * self._Nm
        self._total_energy = (Np * C) * (Ns * Nm * Vnom)  # Wh
        self._SoC_Energy = (SoC/100) * self._total_energy
        if C_rate is not None:
            self._C_rate = C_rate
        if DoD is not None:
            self.setDoD(DoD)
        else:
            # Configura DoD padrão de 20% se não especificado
            self.setDoD(0.8)

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

    def Energy2SoC(self, energy: float) -> float:
        """
        Calcula o SoC da bateria baseado na energia armazenada
        :param float energy: Energia total armazenada (Wh)
        :return float: Estado de carga (%)
        """
        return (energy * 100) / self._total_energy

    def setCurrent(self, power: float) -> (float | float):
        """
        Calcula a corrente por célula baseada na potência requerida
        :param float power: Potência requerida (W)
        :return float i_sat: Corrente por célula (A)
        :return float p_reject: Potência rejeitada (kW)
        """
        i = power / self._v_banco
        i_sat = np.clip(i, -self._C_rate * self._Np * self._C, self._C_rate * self._Np * self._C)  # Limita corrente usando taxa C
        i_reject = i - i_sat                                                 # Calcula corrente rejeitada
        p_reject = (i_reject * self._v_banco)/1000                           # Calcula potência rejeitada
        return i_sat, p_reject

    def getTotalEnergy(self) -> float:
        """
        Retorna a energia total armazenada na bateria
        :return float: Energia total (Wh)
        """
        return self._total_energy
    
    
    def updateEnergy(self, current: float, dt: float) -> (float | float | float):
        """
        Atualiza a energia total da bateria usando contador de Coulomb
        :param float current: Corrente da bateria (A, + carga, - descarga)
        :param float dt: Intervalo de tempo (s)
        :return float SoC: SoC da bateria
        :return float v_banco: Tensão total do pack de bateria
        :return float p_reject: Potência rejeitada (kW)
        """
        # Calcula variação de energia
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

    def setC_rate(self, C_rate: float) -> None:
        """
        Define a taxa C máxima permitida para a bateria.
        :param float C_rate: Taxa C desejada
        """
        if C_rate <= 0:
            raise ValueError("A taxa C deve ser positiva.")
        self._C_rate = C_rate

    def setDoD(self, DoD: float) -> None:
        """
        Define o Depth of Discharge (DoD) da bateria.
        :param float DoD: DoD desejado (0.0 a 1.0, onde 0.2 = 20%)
        """
        if not 0.0 <= DoD <= 1.0:
            raise ValueError("DoD deve estar entre 0.0 e 1.0")
        
        # Calcula os limites baseado no SoC inicial e DoD
        half_DoD = DoD / 2
        self._min_SoC = self._SoC - (half_DoD * 100)
        self._max_SoC = self._SoC + (half_DoD * 100)
        
        # Garante que os limites não ultrapassem 0% ou 100%
        self._min_SoC = max(0, self._min_SoC)
        self._max_SoC = min(100, self._max_SoC)