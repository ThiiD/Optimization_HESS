import numpy as np
from time import sleep
from math import sqrt

class Uc():
    def __init__(self):
        """Inicializa um banco de supercapacitores com valores padrão"""
        self._C = 3140                                                              
        self._Ns = 40                                                               
        self._Np = 10                                                               
        self._Nm = 5                                                                
        self._v_cap = 3   
        self._Cap_uc = 280                                           
        
        self._SoC_max = 100                                                         
        self._SoC_min = 3                                                           

        # Calcula tensões do banco
        self._v_total = self._v_cap * self._Ns * self._Nm
        self._v_banco = self._v_total * (50/100)  # Inicia com 50% SoC
        
        # Calcula energia total e inicial
        self._C_eq = self._C * self._Np/(self._Ns * self._Nm)  # Capacitância equivalente
        self._total_energy = 0.5 * self._C_eq * (self._v_total**2)
        self._stored_energy = 0.5 * self._C_eq * (self._v_banco**2)
        
        self._SoC = 50  # Estado de carga inicial (%)
        self._C_rate = 8  # Valor padrão para taxa C do UC

    def setParams(self, C: float, Cap_uc: float, Ns: int, Np: int, Nm : int, Vnom: float, SoC: float, C_rate: float = None) -> None:
        """Configura os parâmetros do banco de supercapacitores
        :param float C: Capacitância por célula (F)
        :param float Cap_uc: Capacidade do supercapacitor (Ah)
        :param int Ns: Número de capacitores em série
        :param int Np: Número de strings em paralelo
        :param int Nm: Número de módulos em série
        :param float Vnom: Tensão nominal por célula (V)
        :param float SoC: Estado de carga inicial do banco (%)
        :param float C_rate: Taxa C máxima permitida (opcional)
        :raises ValueError: Se os parâmetros forem inválidos
        """
        if any(x <= 0 for x in [C, Ns, Nm, Vnom]):
            raise ValueError("Todos os parâmetros devem ser positivos")
        
        if not 0 <= SoC <= 100:
            raise ValueError("SoC deve estar entre 0% e 100%")

        self._C = C
        self._Cap_uc = Cap_uc
        self._Ns = Ns
        self._Np = Np
        self._Nm = Nm
        self._v_cap = Vnom
        self._SoC = SoC

        # Recalcula parâmetros
        self._v_total = self._v_cap * self._Ns * self._Nm
        self._C_eq = C * Np/(Ns * Nm)
        self._total_energy = 0.5 * self._C_eq * (self._v_total**2)

        
        self._stored_energy = self._total_energy*(self._SoC/100)
        if self._Np == 0:
            self._v_banco = 0
        else:
            self._v_banco = sqrt((2 * self._stored_energy) / self._C_eq)
        if C_rate is not None:
            self._C_rate = C_rate

    def energy2soc(self, energy: float) -> float:
        """
        Calcula SoC baseado na energia armazenada no banco de UC.
        :param float energy: Energia armazenada (J)
        :return float: Estado de carga do banco (%)
        """
        return (energy / self._total_energy) * 100

    def soc2energy(self, SoC: float) -> float:
        """
        Calcula energia armazenada no banco de UC baseada no SoC.
        :param float SoC: Estado de carga do banco (%)
        :return float: Energia armazenada (J)
        """
        return sqrt((2 * self._total_energy * (SoC / 100)) / self._C_eq)

    def voltage2energy(self, voltage: float) -> float:
        """
        Calcula energia armazenada no banco de UC baseada na tensão.
        :param float voltage: Tensão do banco (V)
        :return float: Energia armazenada (J)
        """
        return 0.5 * (self._C_eq * voltage**2)
    
    def energy2voltage(self, energy: float, SoC:float ) -> float:
        """
        Calcula tensão baseada na energia armazenada no banco de UC.
        :param float energy: Energia armazenada (J)
        :return float: Tensão do banco (V)
        """
        # return np.sqrt((2 * energy) / (self._C_eq))
        return sqrt((SoC * self._total_energy) / (50 * self._C_eq))
    

    def setCurrent(self, power: float) -> (float|float):
        """
        Calcula corrente baseada na potência requerida
        :param float power: Potência requerida (W)
        :return float i_sat: Corrente (A)
        :return float p_reject: Potência rejeitada (kW)
        """
        if self._Np == 0:                                               # Caso não haja banco de supercapacitores (Np == 0)
            i_sat = 0                                                   # Corrente saturada é zerada
            p_reject = power / 1000                                     # Rejeita toda a potência
        else:                                                           # Caso haja banco de supercapacitores
            i = power / self._v_banco                                   # Calculo da corrente inicial, sem limitação
            i_max = self._C_rate * self._Cap_uc * self._Np              # Corrente máxima usando taxa C
            i_sat = np.clip(i, -i_max, i_max)                           # Limita corrente em ambas direções
            i_reject = i - i_sat                                        # Calcula corrente rejeitada
            p_reject = (i_reject * self._v_banco) / 1000                # Calcula potência rejeitada
        return i_sat, p_reject


    def getTotalEnergy(self) -> float:
        """
        Retorna a energia total armazenada no banco de UC
        :return float: Energia total (J)
        """
        return self._total_energy
    
    
    def updateEnergy(self, current: float, dt: float) -> tuple[float, float, float, float, float]:
        """
        Atualiza energia do banco usando a corrente
        :param float current: Corrente do banco (A, + carga, - descarga)
        :param float dt: Intervalo de tempo (s)
        :return tuple[float, float]: (Tensão do banco, Energia armazenada)
        :return float p_reject: Potência rejeitada (kW)
        :return float i_uc: Verdadeira corrente do banco (A)
        :return float p_actual: Potência efetivamente trocada no passo (W), para balanço exato com o barramento
        """
        if self._Np == 0:
            self._SoC = 0
            self._v_banco = 0
            p_reject = 0
            i_uc = 0
            p_actual = 0.0
        else:
            # Calcula variação de energia (P = V*I)
            energy_variation = -1 * self._v_banco * current * dt
            
            # Calcula nova energia
            new_energy = self._stored_energy + energy_variation
            
            # Limita energia baseado no SoC
            max_energy = self._total_energy * (self._SoC_max/100)
            min_energy = self._total_energy * (self._SoC_min/100)
            clip_energy = np.clip(new_energy, min_energy, max_energy)     
            
            p_reject = -1*((new_energy - clip_energy) / dt) / 1000         # Potência rejeitada (kW)
            i_uc = -1 * ((clip_energy - self._stored_energy) / dt) / self._v_banco

            # Potência efetiva no passo (W): usa variação de energia para balanço exato (evita usar V_final)
            p_actual = - (clip_energy - self._stored_energy) / dt

            # Atualiza estados
            self._stored_energy = clip_energy
            self._SoC = (self._stored_energy / self._total_energy) * 100
            self._v_banco = self.energy2voltage(clip_energy, self._SoC)
            self.i_uc = i_uc
        return self._SoC, self._v_banco, p_reject, i_uc, p_actual

    def setC_rate(self, C_rate: float) -> None:
        """
        Define a taxa C máxima permitida para o supercapacitor.
        :param float C_rate: Taxa C desejada
        """
        if C_rate <= 0:
            raise ValueError("A taxa C deve ser positiva.")
        self._C_rate = C_rate


    def getSoC(self) -> float:
        return self._SoC


    def verificaPotencia(self, Ed : float, dt : float) -> (float):
        """
        Método para verificar se o banco consegue absorver/fornecer energia
        :param float E_d: Energia que se deseja absorver/fornecer
        :param float dt: Tempo em segundos para se absorver a energia
        return power: potencia máxima que pode ser gerenciada pelo 
        """
        # ---------------------------------------- Restrição por Estado de Carga ----------------------------------------
        
        energia_maxima_absorvivel = (self._SoC_max/100) * self._total_energy - self._total_energy
    
        energia_minima_absorvivel = (self._SoC_min/100) * self._total_energy - self._total_energy

        clip_energy = np.clip(Ed, energia_minima_absorvivel, energia_maxima_absorvivel)

        # ------------------------------------------- Restrição por Corrente --------------------------------------------
        i_max = self._C_rate * self._Cap_uc * self._Np              # Corrente máxima usando taxa C

        corrente_maxima_absorvivel = i_max - self.i_uc
        corrente_minima_absorvivel = (-1* i_max) - self.i_uc

        corrente_desejada = (Ed * dt) / self._v_banco 

        clip_current = np.clip(corrente_desejada, corrente_minima_absorvivel, corrente_maxima_absorvivel)

        clip_energy_por_corrente = (self._v_banco * clip_current) / dt

        return min([clip_energy, clip_energy_por_corrente])