# charts.py

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class ChartBuilder:

    @staticmethod
    def build_price_chart(
        prices,
        volumes=None,
    ):

        if len(prices) == 0:

            fig = go.Figure()

            fig.update_layout(
                height=450
            )

            return fig

        df = pd.DataFrame({
            "price": prices
        })

        # EMA

        df["ema5"] = (
            df["price"]
            .ewm(span=5)
            .mean()
        )

        df["ema20"] = (
            df["price"]
            .ewm(span=20)
            .mean()
        )

        df["ema60"] = (
            df["price"]
            .ewm(span=60)
            .mean()
        )

        # =========================
        # 圖表
        # =========================

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.7, 0.3],
        )

        # =========================
        # 價格
        # =========================

        fig.add_trace(
            go.Scatter(
                y=df["price"],
                name="Price",
                mode="lines",
                line=dict(width=3),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                y=df["ema5"],
                name="EMA5",
                mode="lines",
                line=dict(width=1.5),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                y=df["ema20"],
                name="EMA20",
                mode="lines",
                line=dict(width=1.5),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                y=df["ema60"],
                name="EMA60",
                mode="lines",
                line=dict(width=1.5),
            ),
            row=1,
            col=1,
        )

        # =========================
        # 成交量
        # =========================

        if volumes and len(volumes) > 0:

            fig.add_trace(
                go.Bar(
                    y=volumes,
                    name="Volume",
                ),
                row=2,
                col=1,
            )

        # =========================
        # Layout
        # =========================

        fig.update_layout(

            height=450,

            margin=dict(
                l=5,
                r=5,
                t=10,
                b=5,
            ),

            hovermode="x unified",

            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

        fig.update_xaxes(
            showgrid=False
        )

        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.3
        )

        return fig
