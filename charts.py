import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots


class ChartBuilder:

    # =========================
    # EMA
    # =========================

    @staticmethod
    def calculate_ema(

        prices,

        span,

    ):

        if len(prices) == 0:

            return []

        return (

            pd.Series(prices)

            .ewm(

                span=span,

                adjust=False,

            )

            .mean()

            .tolist()

        )

    # =========================
    # SMA
    # =========================

    @staticmethod
    def calculate_sma(

        prices,

        period,

    ):

        if len(prices) == 0:

            return []

        return (

            pd.Series(prices)

            .rolling(period)

            .mean()

            .tolist()

        )

    # =========================
    # Professional TradingView Chart
    # =========================

    @staticmethod
    def build_price_chart(

        prices,

        volumes,

    ):

        if len(prices) == 0:

            fig = go.Figure()

            fig.update_layout(

                template="plotly_dark",

                height=430,

                margin=dict(

                    l=10,

                    r=10,

                    t=20,

                    b=10,

                ),

            )

            return fig

        # =========================
        # Moving Average
        # =========================

        ema5 = ChartBuilder.calculate_ema(

            prices,

            5,

        )

        ema20 = ChartBuilder.calculate_ema(

            prices,

            20,

        )

        ema60 = ChartBuilder.calculate_ema(

            prices,

            60,

        )

        sma20 = ChartBuilder.calculate_sma(

            prices,

            20,

        )

        # =========================
        # Figure
        # =========================

        fig = make_subplots(

            rows=2,

            cols=1,

            shared_xaxes=True,

            vertical_spacing=0.03,

            row_heights=[0.75, 0.25],

        )

        # =========================
        # Price
        # =========================

        fig.add_trace(

            go.Scatter(

                x=list(range(len(prices))),

                y=prices,

                mode="lines",

                name="Price",

                line=dict(

                    color="#00E5FF",

                    width=3,

                ),

                hovertemplate=

                "<b>Price</b><br>"

                "Index : %{x}<br>"

                "Price : %{y:.2f}"

                "<extra></extra>",

            ),

            row=1,

            col=1,

        )

        # =========================
        # EMA5
        # =========================

        fig.add_trace(

            go.Scatter(

                x=list(range(len(ema5))),

                y=ema5,

                mode="lines",

                name="EMA5",

                line=dict(

                    color="#FFD54F",

                    width=2,

                ),

            ),

            row=1,

            col=1,

        )

        # =========================
        # EMA20
        # =========================

        fig.add_trace(

            go.Scatter(

                x=list(range(len(ema20))),

                y=ema20,

                mode="lines",

                name="EMA20",

                line=dict(

                    color="#FF7043",

                    width=2,

                ),

            ),

            row=1,

            col=1,

        )

        # =========================
        # EMA60
        # =========================

        fig.add_trace(

            go.Scatter(

                x=list(range(len(ema60))),

                y=ema60,

                mode="lines",

                name="EMA60",

                line=dict(

                    color="#AB47BC",

                    width=2,

                ),

            ),

            row=1,

            col=1,

        )

        # =========================
        # SMA20
        # =========================

        fig.add_trace(

            go.Scatter(

                x=list(range(len(sma20))),

                y=sma20,

                mode="lines",

                name="SMA20",

                line=dict(

                    color="#66BB6A",

                    width=2,

                    dash="dot",

                ),

            ),

            row=1,

            col=1,

        )

        # =========================
        # 成交量（台股紅漲綠跌）
        # =========================

        volume_colors = []

        for i in range(len(volumes)):

            if i == 0:

                volume_colors.append("#9E9E9E")

            else:

                # 台股：上漲=紅、下跌=綠

                if prices[i] >= prices[i - 1]:

                    volume_colors.append("#E53935")

                else:

                    volume_colors.append("#2EAF5D")

        fig.add_trace(

            go.Bar(

                x=list(range(len(volumes))),

                y=volumes,

                name="Volume",

                marker=dict(

                    color=volume_colors,

                    line=dict(

                        width=0,

                    ),

                ),

                opacity=0.85,

                hovertemplate=

                "<b>Volume</b><br>"

                "Index : %{x}<br>"

                "Volume : %{y}"

                "<extra></extra>",

            ),

            row=2,

            col=1,

        )

        # =========================
        # TradingView Layout
        # =========================

        fig.update_layout(

            template="plotly_dark",

            height=430,

            hovermode="x unified",

            paper_bgcolor="#111111",

            plot_bgcolor="#111111",

            margin=dict(

                l=10,

                r=10,

                t=20,

                b=10,

            ),

            legend=dict(

                orientation="h",

                y=1.03,

                x=0,

                bgcolor="rgba(0,0,0,0)",

            ),

        )

        fig.update_xaxes(

            showgrid=False,

            zeroline=False,

            showline=False,

        )

        fig.update_yaxes(

            showgrid=True,

            gridcolor="rgba(255,255,255,0.08)",

            zeroline=False,

        )

        # =========================
        # 自動判斷趨勢背景
        # =========================

        if len(ema20) > 0 and len(ema60) > 0:

            if ema20[-1] >= ema60[-1]:

                bg_color = "rgba(255,0,0,0.05)"

            else:

                bg_color = "rgba(0,180,0,0.05)"

            fig.add_vrect(

                x0=0,

                x1=max(len(prices) - 1, 1),

                fillcolor=bg_color,

                opacity=0.25,

                line_width=0,

                layer="below",

            )

        # =========================
        # 最高價（台股：紅）
        # =========================

        high_price = max(prices)

        high_index = prices.index(high_price)

        fig.add_annotation(

            x=high_index,

            y=high_price,

            text=f"▲ {high_price:.2f}",

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=2,

            arrowcolor="#E53935",

            ax=0,

            ay=-35,

            bgcolor="rgba(229,57,53,0.15)",

            bordercolor="#E53935",

            borderwidth=1,

            font=dict(

                size=12,

                color="#E53935",

            ),

        )

        # =========================
        # 最低價（台股：綠）
        # =========================

        low_price = min(prices)

        low_index = prices.index(low_price)

        fig.add_annotation(

            x=low_index,

            y=low_price,

            text=f"▼ {low_price:.2f}",

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=2,

            arrowcolor="#2EAF5D",

            ax=0,

            ay=35,

            bgcolor="rgba(46,175,93,0.15)",

            bordercolor="#2EAF5D",

            borderwidth=1,

            font=dict(

                size=12,

                color="#2EAF5D",

            ),

        )

        # =========================
        # 最新價格水平線
        # =========================

        fig.add_hline(

            y=prices[-1],

            line_dash="dash",

            line_color="#00E5FF",

            line_width=1.5,

            opacity=0.7,

        )

        # =========================
        # TradingView Crosshair
        # =========================

        fig.update_xaxes(

            showspikes=True,

            spikecolor="#888888",

            spikemode="across",

            spikesnap="cursor",

            spikethickness=1,

        )

        fig.update_yaxes(

            showspikes=True,

            spikecolor="#888888",

            spikemode="across",

            spikesnap="cursor",

            spikethickness=1,

            fixedrange=False,

        )

        # =========================
        # Professional Layout
        # =========================

        fig.update_layout(

            hoverlabel=dict(

                bgcolor="#222222",

                font_size=12,

                font_color="white",

            ),

            dragmode="pan",

            xaxis_rangeslider_visible=False,

        )

        # =========================
        # Return
        # =========================

        return fig
