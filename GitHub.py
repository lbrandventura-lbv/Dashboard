import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("Dashboard Energético")

# =====================================================
# CARREGAMENTO DOS DADOS (GOOGLE SHEETS)
# =====================================================

@st.cache_data
def carregar_dados():

    # URLs
    url_1 = "https://docs.google.com/spreadsheets/d/1LKTWQS7hZsKQyl2igBf5DNSft4xlnJV_I8OgCnu5o0M/export?format=csv"
    url_2 = "https://docs.google.com/spreadsheets/d/1Q5lIXLld0XTHOS8GKL2FQg3kD8GaKvHLEy8rACJ1l4w/export?format=csv"

    # Leitura
    df_Consumo = pd.read_csv(url_1, encoding='latin-1', sep=',', decimal=',', low_memory=False)
    df_Producao = pd.read_csv(url_2, encoding='latin-1', sep=',', decimal=',', low_memory=False)

    # Datetime
    df_Consumo.insert(
        0,
        'Datetime',
        pd.to_datetime(df_Consumo['Data'] + ' ' + df_Consumo['Hora'],
                       format='%d/%m/%Y %H:%M:%S')
    )

    df_Producao.insert(
        0,
        'Datetime',
        pd.to_datetime(df_Producao['Data'] + ' ' + df_Producao['Hora'],
                       format='%d/%m/%Y %H:%M:%S')
    )

    # Remover duplicados
    df_Consumo = df_Consumo.drop_duplicates(subset=['Datetime'])
    df_Producao = df_Producao.drop_duplicates(subset=['Datetime'])

    # Limpeza
    df_Consumo = df_Consumo.drop(columns=['Data', 'Hora', 'Ref. Med.'])
    df_Producao = df_Producao.drop(columns=['Data', 'Hora'])

    # Índice
    df_Consumo.set_index('Datetime', inplace=True)
    df_Producao.set_index('Datetime', inplace=True)

    # =====================================================
    # PRODUÇÃO PV
    # =====================================================

    df_Producao['Potencia_PV'] = df_Producao['Potencia_PV'] / 1000

    indice = pd.date_range(
        df_Producao.index.min(),
        df_Producao.index.max(),
        freq='5min'
    )

    df_Producao = df_Producao.reindex(indice).fillna(0)

    df_Producao['Energia_PV'] = df_Producao['Potencia_PV'] * (5/60)

    df_Producao_15min = df_Producao.resample('15min').agg({
        'Potencia_PV': 'mean',
        'Energia_PV': 'sum'
    })

    # =====================================================
    # UNIÃO
    # =====================================================

    df_total = df_Consumo.join(df_Producao_15min, how='outer')

    indice_15 = pd.date_range(
        df_total.index.min(),
        df_total.index.max(),
        freq='15min'
    )

    df_total = df_total.reindex(indice_15).fillna(0)

    # Energia
    df_total['Energia Ativa'] = df_total['Demanda Ativa'] * 0.25
    df_total['Energia Injetada'] = df_total['Demanda Injetada'] * 0.25

    # Consumo real
    df_total['Consumo Instantaneo'] = np.where(
        df_total['Energia_PV'] > 0,
        df_total['Energia Ativa'] +
        (df_total['Energia_PV'] - df_total['Energia Injetada']),
        df_total['Energia Ativa']
    )

    return df_total


df = carregar_dados()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("Filtros")

data_inicio = st.sidebar.date_input(
    "Data inicial",
    df.index.min().date()
)

data_fim = st.sidebar.date_input(
    "Data final",
    df.index.max().date()
)

periodo_label = st.sidebar.selectbox(
    "Periodicidade",
    ["15 min", "30 min", "1 hora", "1 dia"]
)

mapa = {
    "15 min": "15min",
    "30 min": "30min",
    "1 hora": "1h",
    "1 dia": "1d"
}

periodo = mapa[periodo_label]

tipo = st.sidebar.selectbox(
    "Tipo de gráfico",
    ["Linha", "Barras"]
)

# =====================================================
# FILTRO
# =====================================================

inicio = pd.to_datetime(data_inicio)
fim = pd.to_datetime(data_fim) + pd.Timedelta(days=1)

df_filtrado = df.loc[inicio:fim]

# =====================================================
# RESAMPLE
# =====================================================

df_plot = df_filtrado.resample(periodo).agg({
    'Energia Ativa': 'sum',
    'Consumo Instantaneo': 'sum',
    'Energia Injetada': 'sum',
    'Energia_PV': 'sum',
    'Demanda Ativa': 'mean',
    'Demanda Injetada': 'mean',
    'Potencia_PV': 'mean'
}).reset_index()

# =====================================================
# GRÁFICO ENERGIA
# =====================================================

st.subheader("Energia (kWh)")

if tipo == "Linha":
    fig1 = px.line(
        df_plot,
        x='index',
        y=[
            'Energia Ativa',
            'Consumo Instantaneo',
            'Energia Injetada',
            'Energia_PV'
        ],
        height=600
    )
else:
    fig1 = px.bar(
        df_plot,
        x='index',
        y=[
            'Energia Ativa',
            'Consumo Instantaneo',
            'Energia Injetada',
            'Energia_PV'
        ],
        height=600
    )

st.plotly_chart(fig1, use_container_width=True)

# =====================================================
# GRÁFICO POTÊNCIA
# =====================================================

st.subheader("Potência / Demanda (kW)")

if tipo == "Linha":
    fig2 = px.line(
        df_plot,
        x='index',
        y=[
            'Demanda Ativa',
            'Demanda Injetada',
            'Potencia_PV'
        ],
        height=600
    )
else:
    fig2 = px.bar(
        df_plot,
        x='index',
        y=[
            'Demanda Ativa',
            'Demanda Injetada',
            'Potencia_PV'
        ],
        height=600
    )

st.plotly_chart(fig2, use_container_width=True)