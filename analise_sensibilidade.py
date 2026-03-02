import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

fig_width_cm = 24/2.4
fig_height_cm = 18/2.4

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

perfil_desejado = "Araxá"

dir_perfil = {"Conceição do Mato Dentro"    :   {"Arquivo"             :   "CR-3112_28-09-24_AGGREGATED",
                                                 "diretorio_input"     :   "data\CR-3112_28-09-24_AGGREGATED.xlsx",
                                                 "diretorio_output"    :   "Resultados Utilizados\\CR-3112_28-09-24_AGGREGATED\\",
                                                },
                "Araxá"                     :   {"Arquivo"             :   "UMAX_18-10-24",
                                                 "diretorio_input"     :   r"Resultados Utilizados\UMAX_18-10-24_sensibilidade.xlsx",
                                                 "diretorio_output"    :   "Resultados Utilizados\\UMAX_18-10-24\\",}
                                                }

df = pd.read_excel(dir_perfil[perfil_desejado]["diretorio_input"])
print(df)

fig, axs = plt.subplots(1, 2, figsize=(fig_width_cm*1.5, fig_height_cm*.7), sharex=True)
fig.suptitle('Dimensionamento dos Bancos Armazenadores',fontweight='bold')
axs[0].xaxis.set_major_locator(MaxNLocator(integer=True))
axs[0].yaxis.set_major_locator(MaxNLocator(integer=True))
axs[0].plot(df["Unnamed: 0"], df["Nm,b"], color = "tab:brown", linewidth = 2, label = "$N_{m,b}$")
axs[0].plot(df["Unnamed: 0"], df["Nm,uc"], color = "tab:pink", linewidth = 2, label = "$N_{m,uc}$")
axs[0].grid()
axs[0].set_xlabel("Id.")
axs[0].set_ylabel("Número de Módulos")
axs[0].set_xlim([0,15])
axs[0].legend()

axs[1].xaxis.set_major_locator(MaxNLocator(integer=True))
axs[1].yaxis.set_major_locator(MaxNLocator(integer=True))
axs[1].plot(df["Unnamed: 0"], df["Np,b"], color = "tab:brown", linewidth = 2, label = "$N_{p,b}$")
axs[1].plot(df["Unnamed: 0"], df["Np,uc"], color = "tab:pink", linewidth = 2, label = "$N_{p,uc}$")
axs[1].grid()
axs[1].set_xlabel("Id.")
axs[1].set_ylabel("Número de Strings")
axs[1].set_xlim([0,15])
axs[1].legend()
plt.tight_layout()
plt.savefig(f"{dir_perfil[perfil_desejado]["diretorio_output"]}_sensibilidade_dimensionamento_banco.pdf", bbox_inches="tight")
plt.show(block=False)


plt.figure(figsize=(fig_width_cm*1.5, fig_height_cm/1.5))
plt.plot(df["Unnamed: 0"], df["Volume Total [L]"], color = "tab:cyan", linewidth = 2, label = "Volume [L]")
plt.legend()
plt.xlabel("Id.")
plt.ylabel("Volume Total [L]")
plt.title("Volume total ocupado pelos bancos armazenadores")
plt.hlines(1415, 0, 15, color = "tab:red", linewidth = 2)
plt.text(0.5, 1420, f"Volume de Limiar = 1415 L", ha='left', va='bottom', color='tab:red')
plt.xlim([0,15])
plt.ylim([700, 1600])
plt.grid()
plt.tight_layout()
plt.savefig(f"{dir_perfil[perfil_desejado]["diretorio_output"]}_sensibilidade_volume_total.pdf", bbox_inches="tight")
plt.show(block=False)


plt.figure(figsize=(fig_width_cm*1.5, fig_height_cm/1.5))
plt.plot(df["Unnamed: 0"], df["Pth [kW]"], color = "tab:green", linewidth = 2, label = "Pth [kW]")
plt.legend()
plt.xlabel("Id.")
plt.ylabel("Potência de Limiar [kW]")
plt.title("Potência de limiar")
plt.xlim([0,15])
plt.grid()
plt.tight_layout()
plt.savefig(f"{dir_perfil[perfil_desejado]["diretorio_output"]}_sensibilidade_potencia_de_limiar.pdf", bbox_inches="tight")
plt.show(block=False)


plt.figure(figsize=(fig_width_cm*1.5, fig_height_cm/1.5))
plt.plot(df["Unnamed: 0"], df["VPL [R$]"], color = "black", linewidth = 2, label = "VPL [R\$]")
plt.legend()
plt.xlabel("Id.")
plt.ylabel("Valor Presente Líquido [5 anos]")
plt.title("Valor Presente Líquido")
plt.xlim([0,15])
plt.grid()
plt.tight_layout()
plt.savefig(f"{dir_perfil[perfil_desejado]["diretorio_output"]}_sensibilidade_vpl.pdf", bbox_inches="tight")
plt.show(block=True)