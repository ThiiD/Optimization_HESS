import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


dados = "UMAX_18-10-24.xlsx"
dados_name = dados.split(".")[0]
sheet = "Log"

path_dados = "data/"
path_figuras = "Figuras/" + dados_name + "/"


dir_dados = path_dados + dados
dir_output = path_figuras + dados_name + "_analise_perfil.csv"
print(dir_output)

df = pd.read_excel(dir_dados, sheet_name = sheet)

print(df)

try:
    corrente = df["fa08_m2amps"]
    tensao = df["fa00_altoutvolts"]
except:
    corrente = df["ai_04_m2amps"]
    tensao = df["ai_11_altoutvolts"]

potencia = corrente * tensao

plt.figure()
plt.plot(potencia)
plt.show()

max_corrente = max(corrente)                                    # Ampere [A]
min_corrente = min(corrente)                                    # Ampere [A]

max_tensao = max(tensao)                                        # Volts [V]
min_tensao = min(tensao)                                        # Volts [V]

max_power = max(potencia)  / 1000                               # kilo-Watts [kW]
min_power = min(potencia)  / 1000                               # kilo-Watts [kW]

potencia_consumida = potencia[potencia > 0]                     # Watts [W]
potencia_dissipada = potencia[potencia < 0]                     # Watts [W]

energia_consumida = potencia_consumida.sum() / 3600 / 1000      # kilo-watts-hora [kWh]
energia_dissipada = potencia_dissipada.sum() / 3600 / 1000      # kilo-watts-hora [kWh]

media_potencia_consumida = potencia_consumida.mean() / 1000     # kilo-watt [kW]
media_potencia_dissipada = potencia_dissipada.mean() / 1000     # kilo-watt [kW]

tempo_potencia_consumida = len(potencia_consumida)              # Segundos [s]
tempo_potencia_dissipada = len(potencia_dissipada)              # Segundos [s]

relacao_consumo_dissipada = -1 * (energia_dissipada / energia_consumida)

dict = {"Corrente Máxima"                       :   str(round(max_corrente,2)).replace(".", ",") + " A",
        "Corrente Mínima"                       :   str(round(min_corrente,2)).replace(".", ",") + " A",
        "Tensão Máxima"                         :   str(round(max_tensao,2)).replace(".", ",") + " V",
        "Tensão Mínima"                         :   str(round(min_tensao,2)).replace(".", ",") + " V",
        "Potência Máxima"                       :   str(round(max_power,2)).replace(".", ",") + " kW",
        "Potência Mínima"                       :   str(round(min_power,2)).replace(".", ",") + " kW",
        "Energia Consumida"                     :   str(round(energia_consumida,2)).replace(".", ",") + " kWh",
        "Energia Dissipada"                     :   str(round(energia_dissipada,2)).replace(".", ",") + " kWh",
        "Média Potência Consumida"              :   str(round(media_potencia_consumida,2)).replace(".", ",") + " kW",
        "Média Potência Dissipada"              :   str(round(media_potencia_dissipada,2)).replace(".", ",") + " kW",
        "Tempo de Potência Consumida"           :   str(round(tempo_potencia_consumida,2)).replace(".", ",") + " s",
        "Tempo de Potência Dissipada"           :   str(round(tempo_potencia_dissipada,2)).replace(".", ",") + " s",
        "Relação entre Dissipada e Consumida"   :   str(round(relacao_consumo_dissipada,2)).replace(".", ",")}

print(dict)

df2 = pd.Series(dict).reset_index()
df2.columns = ["Parâmetro Observado", "Valor"]
df2.to_csv(dir_output, index=False, sep=";")
