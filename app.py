# app.py
"""
Streamlit Dashboard Demo listo para Render
Autor: Cesar
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# Configuración para Render (headless y puerto dinámico)
port = int(os.environ.get("PORT", 8501))  # Render asigna el puerto en $PORT
st.set_page_config(layout="wide", page_title="Parts Inventory Dashboard")

# -----------------------------
# Función para generar datos de ejemplo
# -----------------------------
def generate_sample_data(n_products=50, n_pos=100):
    np.random.seed(42)
    product_lines = ["Engine", "Electrical", "Brake", "Suspension", "Body", "Interior"]
    skus = [f"SKU-{i:03d}" for i in range(1, n_products+1)]
    
    df_inventory = pd.DataFrame({
        "SKU": skus,
        "ProductLine": np.random.choice(product_lines, size=n_products),
        "QtyOnHand": np.random.randint(0, 100, size=n_products),
        "ReorderPoint": np.random.randint(10, 50, size=n_products),
        "LastCountDate": [datetime.today().date() - pd.to_timedelta(np.random.randint(0, 180), unit='d') for _ in range(n_products)]
    })

    df_inventory["NextScheduledCount"] = df_inventory["LastCountDate"] + pd.to_timedelta(90, unit='d')
    df_inventory["Variance%"] = np.round(np.random.uniform(-20, 40, size=n_products), 1)

    po_numbers = [f"PO-{1000+i}" for i in range(n_pos)]
    po_dates = [datetime.today().date() - pd.to_timedelta(np.random.randint(0, 120), unit='d') for _ in range(n_pos)]
    
    df_purchases = pd.DataFrame({
        "PO": po_numbers,
        "ProductLine": np.random.choice(product_lines, size=n_pos),
        "SKU": np.random.choice(skus, size=n_pos),
        "QtyOrdered": np.random.randint(1, 500, size=n_pos),
        "QtyReceived": lambda df: np.random.randint(0, df["QtyOrdered"]+1),
        "OrderDate": po_dates,
        "ETA": [d + pd.to_timedelta(np.random.randint(1, 30), unit='d') for d in po_dates],
        "Status": np.random.choice(["Open", "Partially Received", "Closed", "Cancelled"], size=n_pos, p=[0.4,0.2,0.35,0.05])
    })
    df_purchases["QtyReceived"] = [np.random.randint(0, q+1) for q in df_purchases["QtyOrdered"]]

    # Asegurar que las columnas de fecha son Timestamps
    df_inventory["LastCountDate"] = pd.to_datetime(df_inventory["LastCountDate"])
    df_inventory["NextScheduledCount"] = pd.to_datetime(df_inventory["NextScheduledCount"])
    df_purchases["OrderDate"] = pd.to_datetime(df_purchases["OrderDate"])
    df_purchases["ETA"] = pd.to_datetime(df_purchases["ETA"])

    return df_inventory, df_purchases

# -----------------------------
# Sidebar: Datos y filtros
# -----------------------------
st.sidebar.header("Data Source")
use_sample = st.sidebar.checkbox("Use sample data", value=True)

if use_sample:
    df_inv, df_pur = generate_sample_data()
else:
    inv_file = st.sidebar.file_uploader("Inventory CSV/Excel", type=["csv","xlsx"])
    pur_file = st.sidebar.file_uploader("Purchases CSV/Excel", type=["csv","xlsx"])
    if inv_file:
        df_inv = pd.read_csv(inv_file) if inv_file.name.endswith(".csv") else pd.read_excel(inv_file)
    else:
        df_inv, _ = generate_sample_data()
    if pur_file:
        df_pur = pd.read_csv(pur_file) if pur_file.name.endswith(".csv") else pd.read_excel(pur_file)
    else:
        _, df_pur = generate_sample_data()

# -----------------------------
# Filtros
# -----------------------------
st.sidebar.header("Filters")
product_lines = sorted(df_inv["ProductLine"].unique())
selected_lines = st.sidebar.multiselect("Product Line", options=product_lines, default=product_lines)

min_date = df_pur["OrderDate"].min().date()
max_date = df_pur["OrderDate"].max().date()
date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date))

# Convertir tipos para filtrar
start_date = pd.to_datetime(date_range[0])
end_date = pd.to_datetime(date_range[1])
df_pur["OrderDate"] = pd.to_datetime(df_pur["OrderDate"], errors="coerce")

# Filtrar
df_inv_f = df_inv[df_inv["ProductLine"].isin(selected_lines)].copy()
df_pur_f = df_pur[
    (df_pur["ProductLine"].isin(selected_lines)) &
    (df_pur["OrderDate"].between(start_date, end_date))
].copy()

# -----------------------------
# Dashboard
# -----------------------------
st.title("Parts Inventory & Purchasing Dashboard")

# KPIs
st.subheader("KPI Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total SKUs", len(df_inv_f))
col2.metric("Total Qty On Hand", df_inv_f["QtyOnHand"].sum())
stockout_rate = round((df_inv_f["QtyOnHand"]==0).sum()/len(df_inv_f)*100,1)
col3.metric("Stockout Rate", f"{stockout_rate}%")

# Inventory by Product Line
st.subheader("Inventory by Product Line")
inv_by_line = df_inv_f.groupby("ProductLine")["QtyOnHand"].sum().reset_index()
fig, ax = plt.subplots()
ax.bar(inv_by_line["ProductLine"], inv_by_line["QtyOnHand"], color="skyblue")
ax.set_ylabel("Qty On Hand")
ax.set_xlabel("Product Line")
ax.set_title("Inventory by Product Line")
st.pyplot(fig)

# Cycle Count Tracker
st.subheader("Cycle Count Tracker")
tracker = df_inv_f[["SKU","ProductLine","LastCountDate","NextScheduledCount","Variance%"]].copy()
tracker["DaysOverdue"] = (pd.Timestamp.today() - tracker["NextScheduledCount"]).dt.days
st.dataframe(tracker.style.format({"LastCountDate":"%Y-%m-%d","NextScheduledCount":"%Y-%m-%d","Variance%":"{:.1f}%"}))

# Purchase Activity Log
st.subheader("Purchase Activity Log")
st.dataframe(df_pur_f[["PO","ProductLine","SKU","QtyOrdered","QtyReceived","OrderDate","ETA","Status"]])

# -----------------------------
# Ejecutar Streamlit en Render
# -----------------------------
if __name__ == "__main__":
    # En Docker, Streamlit ya se ejecuta con el comando CMD del Dockerfile
    # No necesitamos la configuración adicional para Render
    pass