import streamlit as st

from charts import ChartBuilder


def render_chart(
    prices,
    volumes,
):

    st.subheader("📈 分時趨勢")

    fig = ChartBuilder.build_price_chart(
        prices,
        volumes
    )

    fig.update_layout(
        height=320,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )
