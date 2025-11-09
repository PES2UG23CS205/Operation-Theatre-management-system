import streamlit as st
import plotly.express as px
import pandas as pd

ACCENT = "#16A34A"


def app_header(title: str, subtitle: str = None):
    st.markdown(
        f"""
        <div style='padding:8px 12px;border-radius:16px;background:linear-gradient(90deg,#111827,#0B1220);border:1px solid #1f2937;'>
            <h2 style='margin:0;color:#E5E7EB'>{title}</h2>
            {f"<p style='margin:4px 0 0;color:#9CA3AF'>{subtitle}</p>" if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(msg: str):
    st.info(msg)


def gauge_utilization(util_rate: float):
    df = pd.DataFrame({"label": ["Utilization"], "value": [util_rate]})
    fig = px.bar(df, x="label", y="value")
    fig.update_layout(height=200, yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)