"""
app.py — Supply Chain AI Dashboard (Финальная версия).

Streamlit интерфейс с AI объяснениями через Claude API.

Запуск:
  streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import httpx
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Supply Chain AI",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Стили
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
    .stApp { background: #0a0a0f; color: #e8e8f0; }

    .dash-header { border-bottom: 1px solid #1e1e2e; padding-bottom: 1.5rem; margin-bottom: 2rem; }
    .dash-title { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2rem; color: #e8e8f0; letter-spacing: -0.03em; margin: 0; }
    .dash-subtitle { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #4a4a6a; margin-top: 0.25rem; letter-spacing: 0.1em; text-transform: uppercase; }

    .counter-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
    .counter-card { background: #111118; border: 1px solid #1e1e2e; border-radius: 8px; padding: 1.25rem 1.5rem; position: relative; overflow: hidden; }
    .counter-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
    .counter-card.critical::before { background: #ff3b5c; }
    .counter-card.high::before     { background: #ff8c3b; }
    .counter-card.medium::before   { background: #f5c842; }
    .counter-card.low::before      { background: #3bff8c; }
    .counter-label { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: #4a4a6a; margin-bottom: 0.5rem; }
    .counter-value { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2.5rem; line-height: 1; }
    .counter-card.critical .counter-value { color: #ff3b5c; }
    .counter-card.high .counter-value     { color: #ff8c3b; }
    .counter-card.medium .counter-value   { color: #f5c842; }
    .counter-card.low .counter-value      { color: #3bff8c; }

    .section-title { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em; text-transform: uppercase; color: #4a4a6a; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #1e1e2e; }

    .rec-card { background: #111118; border: 1px solid #1e1e2e; border-radius: 8px; padding: 1.25rem; margin-bottom: 0.75rem; position: relative; overflow: hidden; }
    .rec-card::before { content: ''; position: absolute; top: 0; left: 0; bottom: 0; width: 3px; }
    .rec-card.p1::before { background: #ff3b5c; }
    .rec-card.p2::before { background: #ff8c3b; }
    .rec-card.p3::before { background: #f5c842; }
    .rec-card.p4::before { background: #3bff8c; }
    .rec-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .rec-location { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #8888aa; }
    .rec-priority { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 3px; letter-spacing: 0.1em; }
    .rec-card.p1 .rec-priority { background: rgba(255,59,92,0.15); color: #ff3b5c; }
    .rec-card.p2 .rec-priority { background: rgba(255,140,59,0.15); color: #ff8c3b; }
    .rec-card.p3 .rec-priority { background: rgba(245,200,66,0.15); color: #f5c842; }
    .rec-card.p4 .rec-priority { background: rgba(59,255,140,0.15); color: #3bff8c; }
    .rec-action { font-size: 0.9rem; color: #c8c8e0; line-height: 1.5; margin-bottom: 0.5rem; }
    .rec-reason { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #4a4a6a; line-height: 1.4; }

    .ai-response { background: #0d0d1a; border: 1px solid #2a2a4a; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; }
    .ai-label { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; color: #5a5aaa; margin-bottom: 0.75rem; }
    .ai-text { font-size: 0.9rem; color: #c8c8e0; line-height: 1.7; white-space: pre-wrap; }

    .api-status { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #4a4a6a; }
    .api-status.ok  { color: #3bff8c; }
    .api-status.err { color: #ff3b5c; }

    .stButton button { background: #111118 !important; border: 1px solid #1e1e2e !important; color: #8888aa !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.75rem !important; letter-spacing: 0.1em !important; border-radius: 6px !important; }
    .stButton button:hover { border-color: #3a3a5a !important; color: #e8e8f0 !important; }
    .stTextInput input { background: #111118 !important; border: 1px solid #1e1e2e !important; color: #e8e8f0 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.85rem !important; border-radius: 6px !important; }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# API клиент
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def fetch_summary():
    try:
        r = httpx.get(f"{API_URL}/alerts/summary", timeout=3.0)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=30)
def fetch_alerts(limit=50):
    try:
        r = httpx.get(f"{API_URL}/alerts?limit={limit}", timeout=3.0)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []

@st.cache_data(ttl=30)
def fetch_metrics(limit=50):
    try:
        r = httpx.get(f"{API_URL}/metrics?limit={limit}", timeout=3.0)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []

@st.cache_data(ttl=30)
def fetch_health():
    try:
        r = httpx.get(f"{API_URL}/health", timeout=3.0)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def fetch_recommendations():
    try:
        from backend.decision import get_summary
        return get_summary()
    except Exception:
        return []

# ---------------------------------------------------------------------------
# AI функции
# ---------------------------------------------------------------------------

def ai_explain_alert(alert: dict, metric: dict = None) -> str:
    try:
        from backend.explainer import explain_alert
        return explain_alert(alert, metric)
    except Exception as e:
        return f"Ошибка AI: {e}"

def ai_daily_report(alerts: list, metrics: list) -> str:
    try:
        from backend.explainer import explain_summary
        return explain_summary(alerts, metrics)
    except Exception as e:
        return f"Ошибка AI: {e}"

def ai_chat(question: str, alerts: list, metrics: list) -> str:
    try:
        from backend.explainer import chat
        return chat(question, context={"alerts": alerts, "metrics": metrics})
    except Exception as e:
        return f"Ошибка AI: {e}"

# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------

def priority_class(p: int) -> str:
    return {1: "p1", 2: "p2", 3: "p3", 4: "p4"}.get(p, "p4")

def priority_label(p: int) -> str:
    return {1: "P1 СРОЧНО", 2: "P2 ВЫСОКИЙ", 3: "P3 СРЕДНИЙ", 4: "P4 НИЗКИЙ"}.get(p, "P4")

def dedup(items: list, keys: list) -> list:
    seen = set()
    result = []
    for item in items:
        key = tuple(item.get(k) for k in keys)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

# ---------------------------------------------------------------------------
# Компоненты
# ---------------------------------------------------------------------------

def render_header(health):
    status_class = "ok" if health else "err"
    status_text = "● API ONLINE" if health else "● API OFFLINE"
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    st.markdown(f"""
    <div class="dash-header">
        <div style="display:flex; justify-content:space-between; align-items:flex-end">
            <div>
                <div class="dash-title">Supply Chain AI</div>
                <div class="dash-subtitle">Decision Support System — Monitoring Dashboard</div>
            </div>
            <div style="text-align:right">
                <div class="api-status {status_class}">{status_text}</div>
                <div class="api-status">{now}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_counters(summary):
    if not summary:
        st.warning("Нет данных от API")
        return
    st.markdown(f"""
    <div class="counter-grid">
        <div class="counter-card critical"><div class="counter-label">Critical</div><div class="counter-value">{summary.get('CRITICAL', 0)}</div></div>
        <div class="counter-card high"><div class="counter-label">High</div><div class="counter-value">{summary.get('HIGH', 0)}</div></div>
        <div class="counter-card medium"><div class="counter-label">Medium</div><div class="counter-value">{summary.get('MEDIUM', 0)}</div></div>
        <div class="counter-card low"><div class="counter-label">Low</div><div class="counter-value">{summary.get('LOW', 0)}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_recommendations(recs):
    st.markdown('<div class="section-title">Рекомендации</div>', unsafe_allow_html=True)
    if not recs:
        st.markdown('<div style="color:#4a4a6a;font-family:JetBrains Mono,monospace;font-size:0.8rem">Рекомендаций нет</div>', unsafe_allow_html=True)
        return
    unique_recs = dedup(recs, ["warehouse_id", "product", "priority"])
    for rec in unique_recs[:6]:
        pc = priority_class(rec["priority"])
        pl = priority_label(rec["priority"])
        reason_short = (rec.get("reason") or "")[:120] + "..."
        st.markdown(f"""
        <div class="rec-card {pc}">
            <div class="rec-header">
                <div class="rec-location">{rec['warehouse_id']} / {rec['product']}</div>
                <div class="rec-priority">{pl}</div>
            </div>
            <div class="rec-action">{rec['action']}</div>
            <div class="rec-reason">{reason_short}</div>
        </div>
        """, unsafe_allow_html=True)

def render_alerts_table(alerts):
    st.markdown('<div class="section-title">Алерты</div>', unsafe_allow_html=True)
    if not alerts:
        st.markdown('<div style="color:#4a4a6a;font-family:JetBrains Mono,monospace;font-size:0.8rem">Алертов нет</div>', unsafe_allow_html=True)
        return
    df = pd.DataFrame(alerts)[["warehouse_id", "product", "alert_type", "severity", "message", "created_at"]].copy()
    df.columns = ["Склад", "Товар", "Тип", "Severity", "Сообщение", "Время"]
    df["Время"] = pd.to_datetime(df["Время"]).dt.strftime("%H:%M %d.%m")
    df = df.drop_duplicates(subset=["Склад", "Товар", "Тип"]).head(10)
    st.dataframe(df, use_container_width=True, hide_index=True,
        column_config={"Сообщение": st.column_config.TextColumn(width="large")})

def render_metrics_table(metrics):
    st.markdown('<div class="section-title">Метрики складов</div>', unsafe_allow_html=True)
    if not metrics:
        st.markdown('<div style="color:#4a4a6a;font-family:JetBrains Mono,monospace;font-size:0.8rem">Метрик нет</div>', unsafe_allow_html=True)
        return
    df = pd.DataFrame(metrics)[["warehouse_id", "product", "days_of_stock", "risk_score", "calculated_at"]].copy()
    df.columns = ["Склад", "Товар", "Дней запаса", "Risk Score", "Время"]
    df["Время"] = pd.to_datetime(df["Время"]).dt.strftime("%H:%M %d.%m")
    df = df.drop_duplicates(subset=["Склад", "Товар"]).head(10)
    st.dataframe(df, use_container_width=True, hide_index=True,
        column_config={
            "Risk Score": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
            "Дней запаса": st.column_config.NumberColumn(format="%.1f дн."),
        })

# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def main():
    health = fetch_health()
    summary = fetch_summary()
    alerts = fetch_alerts()
    metrics = fetch_metrics()
    recs = fetch_recommendations()

    render_header(health)

    # Кнопки управления
    col1, col2, col3 = st.columns([1, 1, 5])
    with col1:
        if st.button("↻ Обновить"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        if st.button("📋 AI Отчёт"):
            st.session_state["show_report"] = True

    st.markdown("<br>", unsafe_allow_html=True)

    # Счётчики
    render_counters(summary)

    # AI ежедневный отчёт
    if st.session_state.get("show_report"):
        st.markdown('<div class="section-title">AI — Ежедневный отчёт</div>', unsafe_allow_html=True)
        with st.spinner("Claude анализирует систему..."):
            report = ai_daily_report(alerts, metrics)
        st.markdown(
            f'<div class="ai-response"><div class="ai-label">● Claude Sonnet — Анализ системы</div>'
            f'<div class="ai-text">{report}</div></div>',
            unsafe_allow_html=True
        )
        if st.button("✕ Закрыть отчёт"):
            st.session_state["show_report"] = False
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # Основной контент
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        render_recommendations(recs)

        # AI чат
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Спросить AI</div>', unsafe_allow_html=True)
        question = st.text_input(
            label="vопрос",
            placeholder="Например: Почему SPB в критическом состоянии?",
            label_visibility="collapsed"
        )
        if st.button("→ Отправить") and question:
            with st.spinner("Claude думает..."):
                answer = ai_chat(question, alerts, metrics)
            st.markdown(
                f'<div class="ai-response"><div class="ai-label">● Claude Sonnet</div>'
                f'<div class="ai-text">{answer}</div></div>',
                unsafe_allow_html=True
            )

    with col_right:
        render_alerts_table(alerts)
        st.markdown("<br>", unsafe_allow_html=True)
        render_metrics_table(metrics)

        # AI объяснение алерта
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">AI — Объяснение алерта</div>', unsafe_allow_html=True)
        unique_alerts = dedup(alerts, ["warehouse_id", "product", "alert_type"])
        if unique_alerts:
            alert_options = {
                f"{a['warehouse_id']}/{a['product']} [{a['severity']}] {a['alert_type']}": a
                for a in unique_alerts[:8]
            }
            selected = st.selectbox(
                label="алерт",
                options=list(alert_options.keys()),
                label_visibility="collapsed"
            )
            if st.button("🔍 Объяснить"):
                alert = alert_options[selected]
                metric = next(
                    (m for m in metrics
                     if m["warehouse_id"] == alert["warehouse_id"]
                     and m["product"] == alert["product"]),
                    None
                )
                with st.spinner("Claude анализирует..."):
                    explanation = ai_explain_alert(alert, metric)
                st.markdown(
                    f'<div class="ai-response"><div class="ai-label">● Claude Sonnet — Анализ алерта</div>'
                    f'<div class="ai-text">{explanation}</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div style="color:#4a4a6a;font-family:JetBrains Mono,monospace;font-size:0.8rem">Алертов нет</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
