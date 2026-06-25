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

        df = pd.DataFrame({
            "price": prices
        })

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

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
        )

        fig.add_trace(
            go.Scatter(
                y=df["price"],
                name="Price",
                mode="lines",
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                y=df["ema5"],
                name="EMA5",
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                y=df["ema20"],
                name="EMA20",
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                y=df["ema60"],
                name="EMA60",
            ),
            row=1,
            col=1,
        )

        if volumes:

            fig.add_trace(
                go.Bar(
                    y=volumes,
                    name="Volume",
                ),
                row=2,
                col=1,
            )

        fig.update_layout(
            height=700,
            showlegend=True,
            margin=dict(
                l=20,
                r=20,
                t=40,
                b=20,
            ),
        )

        return fig
