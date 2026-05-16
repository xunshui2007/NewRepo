import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, date, timedelta
import time
import warnings
import os
import sys

os.environ["TQDM_DISABLE"] = "1"
os.environ["TQDM_POSITION"] = "-1"

# patch tqdm to prevent stderr crash in Streamlit
import tqdm as _tqdm
class _SilentTqdm:
    def __init__(self, *a, **kw): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __iter__(self): return iter([])
    def update(self, *a): pass
    def close(self): pass
    def set_description(self, *a): pass
_tqdm.tqdm = _SilentTqdm

warnings.filterwarnings("ignore")

st.set_page_config(page_title="A股尾盘选股系统", layout="wide")

st.markdown("""
<style>
.title { font-size: 2rem; font-weight: bold; }
.subtitle { font-size: 0.95rem; color: #888; margin-top: -10px; margin-bottom: 20px; }
.filter-pass { color: #4CAF50; font-weight: bold; }
.filter-fail { color: #f44336; }
.step-header { padding: 8px 0; font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📈 A股尾盘选股系统</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">基于八重筛选条件 · 每日14:50前后精选尾盘标的</div>', unsafe_allow_html=True)

with st.expander("📋 八重筛选条件说明", expanded=True):
    conds = [
        ("① 初筛涨幅", "3% ~ 5%", "确保有一定上涨动力但不过热"),
        ("② 剔除低量比", "量比 > 1", "成交量高于近期平均水平，交投活跃"),
        ("③ 优选换手率", "5% ~ 10%", "换手适中，既不死寂也不过度炒作"),
        ("④ 精选市值", "50亿 ~ 200亿", "中小盘股，弹性好，适合短线操作"),
        ("⑤ 确认量能", "近3日成交量温和放大", "量能逐步释放，不是单日异常"),
        ("⑥ 判断趋势", "5日、10日均线向上发散", "短期多头排列，趋势向好"),
        ("⑦ 验证强度", "盘中始终强于大盘", "相对收益为正，有独立走势"),
        ("⑧ 找买点", "14:50站稳分时均线且创日内新高", "尾盘确认强势，次日惯性上冲概率大"),
    ]
    cols = st.columns(4)
    for i, (t, v, d) in enumerate(conds):
        with cols[i % 4]:
            st.markdown(f"**{t}**  \n`{v}`  \n<small>{d}</small>", unsafe_allow_html=True)

# ==================== 数据层 ====================

@st.cache_data(ttl=15)
def fetch_sina_spot():
    import requests as _req
    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    all_rows = []
    page = 1
    while True:
        params = {"page": page, "num": 80, "sort": "code", "asc": "1", "node": "hs_a", "symbol": "", "_s_r_a": "page"}
        try:
            r = _req.get(url, params=params, headers=headers, timeout=10)
            import json as _json
            items = _json.loads(r.text)
            if not items:
                break
            for item in items:
                all_rows.append({
                    "代码": item.get("symbol", ""),
                    "名称": item.get("name", ""),
                    "最新价": float(item["trade"]) if item.get("trade") not in (None, "", "0") else 0.0,
                    "涨跌额": float(item.get("pricechange", 0)),
                    "涨跌幅": float(item.get("changepercent", 0)),
                    "买入": float(item.get("buy", 0)),
                    "卖出": float(item.get("sell", 0)),
                    "昨收": float(item.get("settlement", 0)),
                    "今开": float(item.get("open", 0)),
                    "最高": float(item.get("high", 0)),
                    "最低": float(item.get("low", 0)),
                    "成交量": float(item.get("volume", 0)),
                    "成交额": float(item.get("amount", 0)),
                    "时间戳": item.get("ticktime", ""),
                })
            if len(items) < 80:
                break
            page += 1
        except Exception:
            break
    df = pd.DataFrame(all_rows)
    return df

@st.cache_data(ttl=30)
def fetch_index_change():
    try:
        idx = ak.stock_zh_index_daily(symbol="sh000001")
        if idx is not None and len(idx) >= 2:
            c2 = float(idx["close"].iloc[-1])
            c1 = float(idx["close"].iloc[-2])
            return round((c2 - c1) / c1 * 100, 2)
    except Exception:
        pass
    return 0.0

@st.cache_data(ttl=300)
def fetch_stock_daily(symbol, days=120):
    for _ in range(2):
        try:
            end = date.today()
            start = end - timedelta(days=days)
            df = ak.stock_zh_a_daily(
                symbol=symbol, start_date=start.isoformat(),
                end_date=end.isoformat(), adjust="qfq",
            )
            if df is not None and len(df) >= 12:
                df = df.sort_values("date", ascending=False).reset_index(drop=True)
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce")
                df["outstanding_share"] = pd.to_numeric(df["outstanding_share"], errors="coerce")
                return df
        except Exception:
            time.sleep(1)
        try:
            import baostock as bs
            bs_code = symbol
            if not symbol.startswith(("sh.", "sz.", "bj.")):
                bs_code = symbol[:2] + "." + symbol[2:]
            lg = bs.login()
            if lg.error_code == "0":
                rs = bs.query_history_k_data_plus(
                    bs_code, "date,close,volume,turn",
                    start_date=(date.today() - timedelta(days=days)).isoformat(),
                    end_date=date.today().isoformat(),
                    frequency="d", adjustflag="2",
                )
                rows = []
                while (rs.error_code == "0") & rs.next():
                    rows.append(rs.get_row_data())
                bs.logout()
                if len(rows) >= 12:
                    df = pd.DataFrame(rows, columns=rs.fields)
                    for c in ["close", "volume", "turn"]:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                    df["outstanding_share"] = np.nan
                    df = df.sort_values("date", ascending=False).reset_index(drop=True)
                    return df
        except Exception:
            pass
    return None

def sym_to_akshare(code):
    c = str(code).strip()
    if c.startswith(("sh", "sz", "bj")):
        return c
    if c.startswith("6"):
        return f"sh{c}"
    if c.startswith(("0", "3", "2")):
        return f"sz{c}"
    if c.startswith(("4", "8")):
        return f"bj{c}"
    return c

# ==================== 筛选逻辑 ====================

def check_vol_trend(volumes):
    if len(volumes) < 5: return False
    v = volumes[:5].astype(float)
    cv = np.std(v[:3]) / np.mean(v[:3]) if np.mean(v[:3]) > 0 else 1
    return v[2] < v[1] < v[0] and cv < 0.4

def check_ma_trend(closes):
    if len(closes) < 12: return False
    c = closes.astype(float)
    ma5 = np.mean(c[:5])
    ma10 = np.mean(c[:10])
    ma5p = np.mean(c[1:6])
    ma10p = np.mean(c[1:11])
    return ma5 > ma10 and ma5 > ma5p and ma10 > ma10p

def build_base_row(row):
    return {
        "代码": str(row["代码"]),
        "名称": row["名称"],
        "最新价": round(float(row["最新价"]), 2),
        "涨跌幅(%)": round(float(row["涨跌幅"]), 2),
    }

def do_screening(spot, max_n, on_progress):
    mask = (spot["涨跌幅"] >= 3) & (spot["涨跌幅"] <= 5)
    pool = spot[mask].copy()
    pool = pool.dropna(subset=["涨跌幅", "最新价", "最高", "最低", "成交量"])
    if len(pool) > max_n:
        pool = pool.head(max_n)

    if len(pool) == 0:
        return None

    idx_chg = fetch_index_change()
    total = len(pool)

    steps = {f"f{i}": [] for i in range(1, 9)}
    steps["f1"] = [build_base_row(row) for _, row in pool.iterrows()]

    for i, (_, row) in enumerate(pool.iterrows()):
        if on_progress:
            on_progress(i, total, row["名称"])

        code = str(row["代码"])
        name = row["名称"]
        price = float(row["最新价"])
        change_pct = float(row["涨跌幅"])
        vol_lots = float(row["成交量"])
        today_high = float(row["最高"])
        today_low = float(row["最低"])

        sym = sym_to_akshare(code)
        daily = fetch_stock_daily(sym)
        if daily is None:
            continue

        hv = daily["volume"].values
        hc = daily["close"].values
        if hv.dtype == object or hc.dtype == object:
            continue

        avg5 = np.mean(hv[:5])
        vol_ratio = (vol_lots * 100) / avg5 if avg5 > 0 else 0
        if vol_ratio <= 1:
            continue

        base = {"代码": code, "名称": name, "最新价": round(price, 2), "涨跌幅(%)": round(change_pct, 2)}
        r2 = {**base, "量比": round(vol_ratio, 2)}
        steps["f2"].append(r2)

        tr = daily["turnover"].iloc[0]
        if pd.isna(tr) or tr <= 0:
            continue
        tr_val = float(tr)
        if 0 < tr_val < 0.5:
            tr_val *= 100
        if not (5 <= tr_val <= 10):
            continue

        r3 = {**r2, "换手率(%)": round(tr_val, 2)}
        steps["f3"].append(r3)

        os = daily["outstanding_share"].iloc[0]
        if pd.isna(os) or os <= 0:
            continue
        mcap_yi = price * float(os) / 1e8
        if not (50 <= mcap_yi <= 200):
            continue

        r4 = {**r3, "总市值(亿)": round(mcap_yi, 1)}
        steps["f4"].append(r4)

        if not check_vol_trend(hv):
            continue
        steps["f5"].append(r4)

        if not check_ma_trend(hc):
            continue
        steps["f6"].append(r4)

        if change_pct <= idx_chg:
            continue
        steps["f7"].append(r4)

        if today_high <= today_low:
            continue
        intra_pos = (price - today_low) / (today_high - today_low)
        if intra_pos < 0.85:
            continue

        r8 = {**r4, "日内强度": f"{intra_pos:.0%}"}
        steps["f8"].append(r8)

    return steps

# ==================== UI ====================

st.markdown("---")

if "spot_data" not in st.session_state:
    st.session_state.spot_data = None
if "f1_cnt" not in st.session_state:
    st.session_state.f1_cnt = 0
if "steps" not in st.session_state:
    st.session_state.steps = None
if "info" not in st.session_state:
    st.session_state.info = None

col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])
with col2:
    initial_scan = st.button("📡 ① 初筛", use_container_width=True)
with col4:
    deep_scan = st.button("🚀 ② 深度分析", type="primary", use_container_width=True)

# ---- Phase 1: 初筛 ----
if initial_scan:
    with st.status("获取实时行情...", expanded=True) as box:
        st.write("📡 获取实时行情...")
        spot = fetch_sina_spot()
        spot = spot[spot["代码"].str.match(r"^(sh|sz|bj)")].copy()
        spot["代码"] = spot["代码"].str[2:]
        st.write(f"✅ A股共 {len(spot)} 只")

        idx_chg = fetch_index_change()
        st.write(f"📊 上证指数: {idx_chg:+.2f}%")

        f1_mask = (spot["涨跌幅"] >= 3) & (spot["涨跌幅"] <= 5)
        f1_cnt = int(f1_mask.sum())
        st.write(f"🎯 条件① 涨幅3%-5%: {f1_cnt} 只")

    st.session_state.spot_data = spot
    st.session_state.f1_cnt = f1_cnt
    st.session_state.steps = None

# ---- Phase 2: 深度分析 ----
if deep_scan:
    if st.session_state.spot_data is None:
        st.warning("请先点击「① 初筛」获取数据")
        st.stop()

    spot = st.session_state.spot_data
    f1_cnt = st.session_state.f1_cnt

    # 默认全量分析初筛结果
    default_n = f1_cnt
    max_allowed = max(f1_cnt, 1)

    with st.container():
        an = st.number_input(
            f"从 {f1_cnt} 只初筛结果中选择分析数量",
            min_value=1, max_value=max_allowed,
            value=default_n,
        )

    box = st.status("深度分析中...", expanded=True)
    try:
        with box:
            idx_chg = fetch_index_change()
            st.write(f"正在分析前 {an} 只股票（共需获取个股数据并检查条件②-⑧）...")

            bar = st.progress(0, text="准备中...")
            txt = st.empty()

            def cb(i, n, nm):
                bar.progress((i + 1) / n)
                txt.text(f"分析中 ({i+1}/{n}): {nm}")

            steps = do_screening(spot, an, cb)
            bar.empty()
            txt.empty()

    except Exception as e:
        st.error(f"❌ 错误: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

    st.session_state.steps = steps
    st.session_state.info = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "f1": f1_cnt,
        "idx": idx_chg,
    }

# ==================== 分步结果展示 ====================

if st.session_state.steps is not None:
    steps = st.session_state.steps
    info = st.session_state.info

    st.markdown("---")
    st.subheader("📊 逐层筛选结果")

    step_names = [
        ("f1", "① 初筛涨幅 3%-5%", ["代码", "名称", "最新价", "涨跌幅(%)"]),
        ("f2", "② 量比 > 1", ["代码", "名称", "最新价", "涨跌幅(%)", "量比"]),
        ("f3", "③ 换手率 5%-10%", ["代码", "名称", "最新价", "涨跌幅(%)", "量比", "换手率(%)"]),
        ("f4", "④ 市值 50亿-200亿", ["代码", "名称", "最新价", "涨跌幅(%)", "量比", "换手率(%)", "总市值(亿)"]),
        ("f5", "⑤ 近3日量能温和放大", ["代码", "名称", "最新价", "涨跌幅(%)", "量比", "换手率(%)", "总市值(亿)"]),
        ("f6", "⑥ 5/10日均线向上发散", ["代码", "名称", "最新价", "涨跌幅(%)", "量比", "换手率(%)", "总市值(亿)"]),
        ("f7", "⑦ 盘中强于大盘", ["代码", "名称", "最新价", "涨跌幅(%)", "量比", "换手率(%)", "总市值(亿)"]),
        ("f8", "⑧ 尾盘买点确认", ["代码", "名称", "最新价", "涨跌幅(%)", "量比", "换手率(%)", "总市值(亿)", "日内强度"]),
    ]

    for key, label, cols in step_names:
        data = steps.get(key, [])
        count = len(data)
        if count == 0:
            st.info(f"❌ {label} — 0 只")
            continue
        with st.expander(f"✅ {label} — {count} 只", expanded=(key == "f8")):
            df = pd.DataFrame(data)
            st.dataframe(df[cols] if all(c in df.columns for c in cols) else df,
                        use_container_width=True, hide_index=True)

    # F8 final result summary
    f8 = steps.get("f8", [])
    if len(f8) > 0:
        st.balloons()
        st.success(f"🎯 最终通过全部8项筛选: **{len(f8)}** 只  (大盘{info['idx']:+.2f}%)")

        df8 = pd.DataFrame(f8)
        for _, r in df8.iterrows():
            c = st.columns([1.2, 1.2, 1, 1, 1, 1, 1.2])
            c[0].markdown(f"**{r['代码']}**")
            c[1].markdown(f"**{r['名称']}**")
            c[2].metric("涨幅", f"{r['涨跌幅(%)']}%")
            c[3].metric("量比", r["量比"])
            c[4].metric("换手率", f"{r['换手率(%)']}%")
            c[5].metric("市值", f"{r['总市值(亿)']}亿")
            c[6].markdown(f"🎯 **{r['日内强度']}**")
            st.divider()

        csv = df8.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 下载CSV", csv, f"选股_{date.today().isoformat()}.csv", "text/csv")

        # ---- PDF导出 ----
        def gen_pdf():
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import io, pathlib

            _script_dir = pathlib.Path(__file__).parent

            def _load_font():
                candidates = [
                    _script_dir / "wqy-microhei.ttc",
                    pathlib.Path(r"C:\Windows\Fonts\simsun.ttc"),
                    pathlib.Path(r"C:\Windows\Fonts\msyh.ttc"),
                ]
                for p in candidates:
                    if p.exists():
                        try:
                            pdfmetrics.registerFont(TTFont("CJK", str(p)))
                            return "CJK", "CJK"
                        except Exception:
                            continue
                # Download fallback
                font_path = _script_dir / "wqy-microhei.ttc"
                if not font_path.exists():
                    import urllib.request
                    url = "https://github.com/anthonyfok/fonts-wqy-microhei/raw/master/wqy-microhei.ttc"
                    urllib.request.urlretrieve(url, font_path)
                try:
                    pdfmetrics.registerFont(TTFont("CJK", str(font_path)))
                    return "CJK", "CJK"
                except Exception:
                    return "Helvetica", "Helvetica-Bold"

            FONT, FONT_BOLD = _load_font()

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                leftMargin=15*mm, rightMargin=15*mm,
                topMargin=15*mm, bottomMargin=15*mm)

            s_title = ParagraphStyle('t', fontName=FONT_BOLD, fontSize=16, spaceAfter=4, alignment=TA_CENTER)
            s_info = ParagraphStyle('i', fontName=FONT, fontSize=9, spaceAfter=12, alignment=TA_CENTER)
            s_h = ParagraphStyle('h', fontName=FONT_BOLD, fontSize=11, spaceBefore=10, spaceAfter=4)
            s_cell = ParagraphStyle('c', fontName=FONT, fontSize=7.5, leading=10)
            s_head = ParagraphStyle('h', fontName=FONT_BOLD, fontSize=7.5, leading=10)

            story = []
            story.append(Paragraph("A股尾盘选股系统 - 筛选报告", s_title))
            today_str = date.today().isoformat()
            story.append(Paragraph(f"{today_str} {info.get('time','')} | 上证指数: {info.get('idx',0):+.2f}% | 条件①通过: {info.get('f1',0)}只", s_info))
            story.append(Spacer(1, 6))

            snames = [
                ("f1","① 涨幅3%-5%"), ("f2","② 量比>1"), ("f3","③ 换手率5%-10%"),
                ("f4","④ 市值50-200亿"), ("f5","⑤ 量能温和放大"), ("f6","⑥ 均线向上发散"),
                ("f7","⑦ 强于大盘"), ("f8","⑧ 尾盘买点确认"),
            ]
            scol_keys = [
                ["代码","名称","最新价","涨跌幅(%)"],
                ["代码","名称","最新价","涨跌幅(%)","量比"],
                ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)"],
                ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)","总市值(亿)"],
                ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)","总市值(亿)"],
                ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)","总市值(亿)"],
                ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)","总市值(亿)"],
                ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)","总市值(亿)","日内强度"],
            ]

            for (key, label), cols in zip(snames, scol_keys):
                data = steps.get(key, [])
                if not data:
                    story.append(Paragraph(f"{label}: 0只", s_h))
                    continue
                df_s = pd.DataFrame(data)
                story.append(Paragraph(f"{label}: {len(data)}只", s_h))

                exist_cols = [c for c in cols if c in df_s.columns]
                table_data = [[Paragraph(c, s_head) for c in exist_cols]]
                for _, r in df_s.iterrows():
                    row = [Paragraph(str(r.get(c, "")), s_cell) for c in exist_cols]
                    table_data.append(row)

                cw = max(12, 170 // len(exist_cols))
                col_w = [cw * mm] * len(exist_cols)
                t = Table(table_data, colWidths=col_w)
                t.setStyle(TableStyle([
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#D9E2F3')]),
                ]))
                story.append(t)
                story.append(Spacer(1, 4))

            if f8:
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"最终通过全部8项: {len(f8)}只", s_h))
                df_last = pd.DataFrame(f8)
                cols_last = ["代码","名称","最新价","涨跌幅(%)","量比","换手率(%)","总市值(亿)","日内强度"]
                table_data = [[Paragraph(c, s_head) for c in cols_last]]
                for _, r in df_last.iterrows():
                    table_data.append([Paragraph(str(r.get(c,"")), s_cell) for c in cols_last])
                cw2 = max(12, 170 // len(cols_last))
                t2 = Table(table_data, colWidths=[cw2 * mm] * len(cols_last))
                t2.setStyle(TableStyle([
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#C00000')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FCE4EC')]),
                ]))
                story.append(t2)

            doc.build(story)
            buf.seek(0)
            return buf.read()

        pdf_bytes = gen_pdf()
        st.download_button("📄 导出PDF", pdf_bytes, f"选股报告_{date.today().isoformat()}.pdf", "application/pdf")

    else:
        st.warning(f"未筛选到完全符合条件的股票（条件①通过{info['f1']}只）")

st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}　|　数据: 新浪财经/Baostock")
