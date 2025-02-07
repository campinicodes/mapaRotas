import folium
from folium.plugins import MarkerCluster
from geopy.distance import geodesic
import numpy as np
import requests
import time
import pandas as pd

# === CONFIGURAÇÃO ===
ORS_API_KEY = "5b3ce3597851110001cf62480c551d49302f4d8a82b84bb558bfef01"  # Insira sua chave da OpenRouteService

# Definição das cidades e coordenadas (adicione coordenadas reais)
zonas = {
    "Zona 1": [
        {"nome": "Marília", "coordenadas": (-22.204331, -49.947414)},
        {"nome": "Lins", "coordenadas": (-21.658995068778335, -49.77034659550775)},
    ],
    "Zona 2": [
        {"nome": "São José do Rio Preto", "coordenadas": (-20.764267580771214, -49.402553967298)},
        {"nome": "Bebedouro", "coordenadas": (-20.915758709956766, -48.48290124338773)},
        {"nome": "Jardinópolis", "coordenadas": (-21.029334109676725, -47.78896164146873)},
        {"nome": "Ribeirão Preto", "coordenadas": (-21.111186656861772, -47.83258500826787)},
        {"nome": "Taquaritinga", "coordenadas": (-21.428459998050414, -48.517948490606685)},
    ],
    "Zona 3": [
        {"nome": "Araras", "coordenadas": (-22.333264964478722, -47.35019378751432)},
    ],
    "Isolada": [
        {"nome": "Presidente Prudente", "coordenadas": (-22.073443351861634, -51.37703185175261)},
    ],
    "Zona São Paulo": [  # Adicionando a Zona São Paulo
        {"nome": "São Paulo", "coordenadas": (-23.573959036433585, -46.68873540203662)},  # Coordenadas fornecidas
    ],
}

# Função para calcular a maior distância entre cidades da mesma zona
def calcular_raio_e_centro(cidades):
    if len(cidades) < 2:
        return 10 * 1000, cidades[0]["coordenadas"]
    
    maior_distancia = 0
    centro = (0, 0)
    for i, cidade1 in enumerate(cidades):
        for j, cidade2 in enumerate(cidades):
            if i < j:
                distancia = geodesic(cidade1["coordenadas"], cidade2["coordenadas"]).km
                if distancia > maior_distancia:
                    maior_distancia = distancia
                    centro = (
                        np.mean([cidade1["coordenadas"][0], cidade2["coordenadas"][0]]),
                        np.mean([cidade1["coordenadas"][1], cidade2["coordenadas"][1]]),
                    )
    return (maior_distancia / 2) * 1000, centro

# Função para obter rotas usando OpenRouteService
def obter_rota(origem, destino):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    
    # Parametrizar os dados corretamente no formato (longitude, latitude)
    params = {
        "api_key": ORS_API_KEY,
        "start": f"{origem['coordenadas'][1]},{origem['coordenadas'][0]}",  # Longitude, Latitude de origem
        "end": f"{destino['coordenadas'][1]},{destino['coordenadas'][0]}"   # Longitude, Latitude de destino
    }
    
    # Realizar a requisição
    response = requests.get(url, params=params)
    
    # Verificar o status da requisição e imprimir o retorno
    if response.status_code == 200:
        data = response.json()
        
        # Verificar se a chave 'features' está presente e contém dados
        if "features" in data and len(data["features"]) > 0:
            feature = data["features"][0]
            rota = feature["geometry"]["coordinates"]  # Rota já em formato de coordenadas (longitude, latitude)
            distancia = feature["properties"]["segments"][0]["distance"] / 1000  # Converter de metros para km
            duracao = feature["properties"]["segments"][0]["duration"] / 60  # Converter de segundos para minutos
            return rota, distancia, duracao
        else:
            print(f"Erro: Dados de direção não encontrados para {origem['nome']} → {destino['nome']}")
    else:
        print(f"Erro na requisição: {response.status_code}")
    
    return None, None, None

# Lista para armazenar os dados da rota para gerar o arquivo .xlsx
rotas_dados = []

# Criar o mapa
mapa = folium.Map(location=list(zonas["Zona 1"][0]["coordenadas"]), zoom_start=6)
marker_cluster = MarkerCluster().add_to(mapa)

# Adicionar cidades e círculos ao mapa
for zona, cidades in zonas.items():
    cor = {"Zona 1": "blue", "Zona 2": "green", "Zona 3": "red", "Isolada": "purple", "Zona São Paulo": "orange"}[zona]
    raio_m, centro = calcular_raio_e_centro(cidades)
    
    for cidade in cidades:
        lat, lon = cidade["coordenadas"]
        folium.Marker(location=(lat, lon), popup=cidade["nome"], icon=folium.Icon(color=cor)).add_to(marker_cluster)
    
    folium.Circle(
        location=centro,
        radius=raio_m,
        color=cor,
        fill=True,
        fill_color=cor,
        fill_opacity=0.3,
    ).add_to(mapa)

# Adicionar rotas entre as cidades com intervalo de 5 minutos entre as requisições
cidades_lista = [cidade for zona in zonas.values() for cidade in zona]
for i in range(len(cidades_lista)):
    for j in range(i + 1, len(cidades_lista)):
        origem = cidades_lista[i]
        destino = cidades_lista[j]
        rota, distancia, duracao = obter_rota(origem, destino)
        if rota:
            # Ajuste para garantir que as coordenadas sejam passadas corretamente
            coordenadas = [(lat, lon) for lon, lat in rota]  # Inverter as coordenadas para (lat, lon)
            
            # Adicionar a rota ao mapa
            folium.PolyLine(
                locations=coordenadas,  # Passar as coordenadas no formato correto
                color="black",
                weight=2.5,
                opacity=0.7,
                tooltip=f"🚗 {origem['nome']} → {destino['nome']}<br>📍 {distancia:.1f} km<br>⏳ {duracao:.0f} min",
            ).add_to(mapa)
            print(f"Rota entre {origem['nome']} e {destino['nome']} adicionada!")  # Log para verificar

            # Salvar o mapa a cada rota
            mapa.save("mapa_interativo_atualizado.html")

            # Adicionar dados das rotas à lista para o arquivo Excel
            rotas_dados.append({
                "Rota": f"{origem['nome']} → {destino['nome']}",
                "Distância (km)": f"{distancia:.1f}",
                "Tempo (min)": f"{duracao:.0f}",
            })

            # Esperar 5 minutos (300 segundos) antes de fazer a próxima requisição
            time.sleep(30)

# Criar um DataFrame a partir dos dados das rotas
df_rotas = pd.DataFrame(rotas_dados)

# Salvar os dados no formato .xlsx
df_rotas.to_excel("dados_rotas.xlsx", index=False)

print("Mapa finalizado e salvo como 'mapa_interativo_atualizado.html'.")
print("Tabela de rotas salva como 'dados_rotas.xlsx'.")
