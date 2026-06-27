"""Streamlit UI for the V1 portfolio backtesting tool.

This is the UI shell only: it collects parameters, calls the pure computation
layer in ``invest_analysis``, and renders charts. It must not contain any
backtest math itself, and the computation layer never imports streamlit.

Run with:

    conda run -n invest streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# The invest_analysis package lives under src/. pytest finds it via
# pyproject.toml's pythonpath, but `streamlit run` does not read that config,
# so add src/ to the import path here.
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from invest_analysis import data_loader as dl
from invest_analysis import metrics as m
from invest_analysis import portfolio as pf
from invest_analysis.assets import (
    get_asset_catalog,
    get_grouped_catalog,
    is_synthetic,
)


REBALANCE_OPTIONS = {
    "不再平衡（买入持有）": "none",
    "月度再平衡": "monthly",
    "季度再平衡": "quarterly",
    "年度再平衡": "annual",
}

# Periodic modes that coincide when the selection is downsampled to annual.
_PERIODIC_MODES = {"monthly", "quarterly", "annual"}


@st.cache_data(show_spinner=False)
def load_catalog_assets(asset_ids: list[str]):
    """Cached wrapper over data_loader.load_assets (UI-layer caching only)."""
    return dl.load_assets(asset_ids)


def render_header() -> None:
    st.title("投资组合回测分析 · V1")
    st.info(
        "**数据口径说明**：黄金、标普 500、纳斯达克 100 为**月度**数据，其余资产为**年度**数据；"
        "数值为原始指数点位 / 价格 / 总回报指数，**未处理汇率**。**现金**为 0% 回报、0 波动的合成资产，"
        "无需数据、频率随其余资产，需至少搭配一个真实资产。**混频对齐规则**：所选资产只要含任一年度资产，"
        "即把月度资产按年末月**降频到年度**再回测；仅当所选资产全为月度时才按月度计算。"
        "**再平衡**按真实日历边界生效：全月度选择下月度 / 季度 / 年度再平衡分别在每月 / 季末 / 年末重置，"
        "结果不同；含年度资产（降为年度）时数据只有年度节点，三者重合。"
    )


def collect_params(catalog: dict) -> tuple[list[str], dict[str, float], str]:
    """Sidebar controls; returns (asset_ids, weights_decimal, rebalance_mode)."""
    st.sidebar.header("回测参数")

    # Build the picker options grouped by category, in display order. Streamlit's
    # multiselect has no native option groups, so insert non-selectable header
    # rows ("—— 股票ETF ——") between groups and filter them back out of the
    # selection. The headers are only visual separators.
    options: list[str] = []
    header_labels: set[str] = set()
    name_to_id: dict[str, str] = {}
    for category_label, members in get_grouped_catalog():
        header = f"—— {category_label} ——"
        options.append(header)
        header_labels.add(header)
        for aid, meta in members:
            options.append(meta["name"])
            name_to_id[meta["name"]] = aid

    selected_names = st.sidebar.multiselect("选择资产", options=options)
    asset_ids = [
        name_to_id[name] for name in selected_names if name not in header_labels
    ]

    weights: dict[str, float] = {}
    if asset_ids:
        st.sidebar.subheader("权重配置（%）")
        default = round(100.0 / len(asset_ids), 2)
        for aid in asset_ids:
            weights[aid] = st.sidebar.number_input(
                catalog[aid]["name"],
                min_value=0.0,
                max_value=100.0,
                value=default,
                step=1.0,
                key=f"w_{aid}",
            )

    rebalance_label = st.sidebar.radio(
        "再平衡模式", options=list(REBALANCE_OPTIONS.keys())
    )
    rebalance = REBALANCE_OPTIONS[rebalance_label]

    # Convert percentages to decimals for the computation layer.
    weights_decimal = {aid: w / 100.0 for aid, w in weights.items()}
    return asset_ids, weights_decimal, rebalance


def _plot_x(index):
    """Plotly x-axis values: convert a monthly PeriodIndex to timestamps."""
    if isinstance(index, pd.PeriodIndex):
        return index.to_timestamp()
    return index


def build_figure(normalized, nav) -> go.Figure:
    """Portfolio nav plus per-asset normalized reference curves."""
    fig = go.Figure()
    x = _plot_x(normalized.index)
    for col in normalized.columns:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=normalized[col],
                name=col,
                mode="lines",
                line=dict(width=1, dash="dot"),
                opacity=0.6,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=_plot_x(nav.index),
            y=nav.values,
            name="组合净值",
            mode="lines",
            line=dict(width=3, color="#d62728"),
        )
    )
    fig.update_layout(
        title="组合净值曲线（起点 = 1）",
        xaxis_title="时间",
        yaxis_title="净值",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    # rangeslider is visual zoom only; it does NOT drive metric recomputation.
    fig.update_xaxes(rangeslider_visible=True)
    return fig


def render_metrics(metrics: dict[str, float]) -> None:
    cols = st.columns(5)
    cols[0].metric("累计收益率", f"{metrics['cumulative_return']:.2%}")
    cols[1].metric("年化收益率", f"{metrics['annualized_return']:.2%}")
    cols[2].metric("年化波动率", f"{metrics['annualized_volatility']:.2%}")
    cols[3].metric("最大回撤", f"{metrics['max_drawdown']:.2%}")
    sharpe = metrics["sharpe_ratio"]
    cols[4].metric("夏普比率", "—" if sharpe != sharpe else f"{sharpe:.2f}")


def main() -> None:
    st.set_page_config(page_title="投资组合回测 · V1", layout="wide")
    catalog = get_asset_catalog()

    render_header()
    asset_ids, weights, rebalance = collect_params(catalog)

    if not asset_ids:
        st.info("请在左侧选择至少一个资产。")
        return

    if all(is_synthetic(aid) for aid in asset_ids):
        st.info("现金没有自己的时间轴，请再选择至少一个真实资产（如黄金 / 标普 500 等）。")
        return

    # Weight-sum check before doing any work (uses validate_weights tolerance).
    total_pct = sum(weights.values()) * 100
    if abs(total_pct - 100.0) > 1e-4:
        st.error(f"权重之和需为 100%，当前为 {total_pct:.2f}%。请调整后再查看结果。")
        return

    try:
        data = load_catalog_assets(asset_ids)
    except ValueError as exc:
        st.error(f"无法加载所选资产：{exc}")
        return

    index_years = (
        data.index.year if isinstance(data.index, pd.PeriodIndex) else data.index
    )
    year_min, year_max = int(min(index_years)), int(max(index_years))
    if year_min >= year_max:
        st.warning("所选资产的共同年份不足以回测。")
        return

    start, end = st.slider(
        "回测区间（年）",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
    )
    st.caption(f"所选资产共同年份范围：{year_min} – {year_max}")

    try:
        sliced = dl.filter_date_range(data, start, end)
        if len(sliced) < 2:
            st.warning("所选区间过短（不足 2 个数据点），无法计算指标。")
            return
        normalized = dl.normalize_prices(sliced)
        nav = pf.backtest_portfolio(normalized, weights, rebalance)
        metrics = m.calculate_metrics(
            nav, periods_per_year=dl.infer_periods_per_year(sliced)
        )
    except ValueError as exc:
        st.error(f"回测失败：{exc}")
        return

    if dl.infer_periods_per_year(sliced) == 1 and rebalance in _PERIODIC_MODES:
        st.info(
            "本次选择含年度资产，已降频到年度，月度 / 季度 / 年度再平衡结果相同；"
            "如需区分不同再平衡频率，请仅选择月度资产（黄金 / 标普 500 / 纳斯达克 100）。"
        )

    render_metrics(metrics)
    st.plotly_chart(build_figure(normalized, nav), use_container_width=True)


if __name__ == "__main__":
    main()
