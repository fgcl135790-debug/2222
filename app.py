import streamlit as st

# 必須放第一個 Streamlit 指令
st.set_page_config(
    page_title="REST PRO",
    page_icon="⚡",
    layout="wide",
)

import pandas as pd

from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine
from market_analyzer import MarketAnalyzer
from charts import ChartBuilder
from exporters import Exporter
