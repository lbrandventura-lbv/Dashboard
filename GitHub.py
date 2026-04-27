import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("Dashboard Consumo e Produção IFSC-SJ")

ARQUIVO_PARQUET = "base_energia.parquet"

# =====================================================
# FUNÇÃO GOOGLE SHEETS
# =====================================================

def carregar_google():

    url_1 = "https://docs.google.com/spreadsheets/d/1LKTWQS7hZsKQyl2igBf5DNSft4xlnJV_I8OgCnu5o0M/export?format=csv"
    url_2 = "https://docs.google.com/spreadsheets/d/1Q5lIXLld0XTHOS8GKL2FQg3kD8GaKvHLEy8rACJ1l4w/export?format=csv"

    df_consumo = pd.read_csv(url_1, sep=",", decimal=",", encoding="latin1", low_memory=False)
    df_producao = pd.read_csv(url_2, sep=",", decimal=",", encoding="latin1", low_memory=False)

    df_consumo["Datetime"] = pd.to_datetime(df_consumo["Data"] + " " + df_consumo["Hora"], dayfirst=True)
    df_producao["Datetime"] = pd.to_datetime(df_producao["Data"] + " " + df_producao["Hora"], dayfirst=True)

    df_consumo.drop_duplicates(subset="Datetime", inplace=True)
    df_producao.drop_duplicates(subset="Datetime", inplace=True)

    df_consumo.drop(columns=["Data", "Hora", "Ref. Med."], inplace=True)
    df_producao.drop(columns=["Data", "Hora"], inplace=True)

    df_consumo.set_index("Datetime", inplace=True)
    df_producao.set_index("Datetime", inplace=True)

    # Produção
    df_producao["Potencia_PV"] = df_producao["Potencia_PV"] / 1000
    df_producao["Energia_PV"] = df_producao["Potencia_PV"] * (5 / 60)

    df_producao = df_producao.resample("15min").agg({
        "Potencia_PV": "mean",
        "Energia_PV": "sum"
    }).fillna(0)

    # Consumo
    df_consumo = df_consumo.resample("15min").mean().fillna(0)

    # União
    df = df_consumo.join(df_producao, how="outer").fillna(0)

    # Cálculos
    df["Energia Ativa"] = df["Demanda Ativa"] * 0.25
    df["Energia Injetada"] = df["Demanda Injetada"] * 0.25

    df["Consumo Instantaneo"] = np.where(
        df["Energia_PV"] > 0,
        df["Energia Ativa"] + (df["Energia_PV"] - df["Energia Injetada"]),
        df["Energia Ativa"]
    )

    return df.sort_index()

# =====================================================
# CARREGAMENTO
# =====================================================

@st.cache_data(ttl=21600)
def carregar_dados():

    if os.path.exists(ARQUIVO_PARQUET):
        df = pd.read_parquet(ARQUIVO_PARQUET)
        df.index = pd.to_datetime(df.index)
        return df

    df = carregar_google()
    df.to_parquet(ARQUIVO_PARQUET, engine="pyarrow", compression="snappy")
    return df

# =====================================================
# BOTÃO ATUALIZAR
# =====================================================

if st.sidebar.button("🔄 Atualizar Base"):
    novo = carregar_google()
    novo.to_parquet(ARQUIVO_PARQUET, engine="pyarrow", compression="snappy")
    st.cache_data.clear()
    st.success("Base atualizada.")

# =====================================================
# LOAD
# =====================================================

df = carregar_dados()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("Filtros")

anos = sorted(df.index.year.unique())
ano_escolhido = st.sidebar.selectbox("Selecione o Ano", anos, index=len(anos)-1)

# =====================================================
# FILTRO ANUAL
# =====================================================

df_ano = df[df.index.year == ano_escolhido]

# =====================================================
# GRÁFICO 1 - ENERGIA (15 MIN FIXO)
# =====================================================

st.subheader(f"Energia - Ano {ano_escolhido}")

fig1 = px.line(
    df_ano.reset_index(),
    x="Datetime",
    y=[
        "Energia Ativa",
        "Consumo Instantaneo",
        "Energia Injetada",
        "Energia_PV"
    ],
    height=600
)

st.plotly_chart(fig1, use_container_width=True)

# =====================================================
# GRÁFICO 2 - POTÊNCIA (15 MIN FIXO)
# =====================================================

st.subheader(f"Potência / Demanda - Ano {ano_escolhido}")

fig2 = px.line(
    df_ano.reset_index(),
    x="Datetime",
    y=[
        "Demanda Ativa",
        "Demanda Injetada",
        "Potencia_PV"
    ],
    height=600
)

st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# BASE MENSAL
# =====================================================

df_mensal = df.resample("ME").agg({
    "Potencia_PV": "mean",
    "Demanda Ativa": "mean",
    "Demanda Injetada": "mean",
    "Energia_PV": "sum",
    "Energia Ativa": "sum",
    "Energia Injetada": "sum",
    "Consumo Instantaneo": "sum"
})

df_mensal["Ano"] = df_mensal.index.year.astype(str)
df_mensal["Mes"] = df_mensal.index.month

meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

# =====================================================
# GRÁFICO 3 - GERAÇÃO MENSAL
# =====================================================

st.subheader("Geração Mensal por Ano")

graf_ger = df_mensal.pivot(index="Mes", columns="Ano", values="Energia_PV")
graf_ger = graf_ger.reindex(range(1,13))
graf_ger.index = meses

fig3 = px.bar(
    graf_ger,
    x=graf_ger.index,
    y=graf_ger.columns,
    barmode="group",
    height=600
)

fig3.update_layout(
    xaxis_title="Mês",
    yaxis_title="Energia Gerada (kWh)"
)

st.plotly_chart(fig3, use_container_width=True)

# =====================================================
# GRÁFICO 4 - CONSUMO MENSAL
# =====================================================

st.subheader("Consumo Mensal por Ano")

graf_cons = df_mensal.pivot(index="Mes", columns="Ano", values="Energia Ativa")
graf_cons = graf_cons.reindex(range(1,13))
graf_cons.index = meses

fig4 = px.bar(
    graf_cons,
    x=graf_cons.index,
    y=graf_cons.columns,
    barmode="group",
    height=600
)

fig4.update_layout(
    xaxis_title="Mês",
    yaxis_title="Energia Consumida (kWh)"
)

st.plotly_chart(fig4, use_container_width=True)
