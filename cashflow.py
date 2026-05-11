import matplotlib.pyplot as plt
import numpy as np

class CashFlow:
    fig_width_cm = 24/2.4
    fig_height_cm = 18/2.4
    def __init__(self, fluxo_caixa):
        """
        Inicializa a classe CashFlow com um array de fluxo de caixa
        
        Args:
            fluxo_caixa: Lista ou array com os valores do fluxo de caixa
        """
        self.fluxo_caixa = np.array(fluxo_caixa)
        
    def plot(self):
        """
        Plota o gráfico do fluxo de caixa
        """
        meses = np.arange(len(self.fluxo_caixa))
        
        plt.figure(figsize=(self.fig_width_cm, self.fig_height_cm))
        
        # Barras para valores positivos (receitas) e negativos (despesas)
        receitas = np.where(self.fluxo_caixa > 0, self.fluxo_caixa, 0)
        despesas = np.where(self.fluxo_caixa < 0, self.fluxo_caixa, 0)
        
        # Plotar receitas em verde
        if np.any(receitas > 0):
            plt.bar(meses, receitas, color='green', alpha=0.7, label='Receitas')
        
        # Plotar despesas em vermelho
        if np.any(despesas < 0):
            plt.bar(meses, despesas, color='red', alpha=0.7, label='Despesas')
        
        # Linha do fluxo de caixa acumulado
        fluxo_acumulado = np.cumsum(self.fluxo_caixa)
        plt.plot(meses, fluxo_acumulado, 'b-', linewidth=2, label='Fluxo Acumulado')
        
        # Linha horizontal em y=0
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        plt.xlabel('Meses')
        plt.ylabel('Fluxo de Caixa (BRL)')
        plt.title('Fluxo de Caixa Mensal')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Adicionar valores nas barras
        for i, valor in enumerate(self.fluxo_caixa):
            if valor < 0:
                plt.text(i, valor + (0.1 if valor > 0 else -0.1), 
                        f'{valor/1000:.0f}k', ha='center', va='bottom' if valor > 0 else 'top', size=18)
        
        plt.tight_layout()
        plt.show(block = False  )
        
    def get_vpl(self, taxa_desconto_mensal):
        """
        Calcula o Valor Presente Líquido (VPL)
        
        Args:
            taxa_desconto_mensal: Taxa de desconto mensal
            
        Returns:
            float: Valor do VPL
        """
        vpl = 0
        for i, fc in enumerate(self.fluxo_caixa):
            vpl += fc / ((1 + taxa_desconto_mensal) ** i)
        return vpl 