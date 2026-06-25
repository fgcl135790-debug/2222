import streamlit as st

st.write("APP START")

from simulation_engine import SimulationEngine
st.write("SIM OK")

from market_analyzer import MarketAnalyzer
st.write("ANALYZER OK")

from charts import ChartBuilder
st.write("CHART OK")

from exporters import Exporter
st.write("EXPORTER OK")

from fugle_provider import FugleProvider
st.write("FUGLE OK")
