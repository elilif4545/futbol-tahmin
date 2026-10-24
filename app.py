from __future__ import annotations

import math
from typing import Any

import streamlit as st

MAX_GOALS = 15

st.set_page_config(
    page_title="Futbol Tahmin Merkezi",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .stApp { background: #f5f7fb; }
      .block-container { max-width: 1500px; padding-top: 1.3rem; padding-bottom: 2.5rem; }
      h1, h2, h3 { color: #172b4d; }
      .hero {
        background: linear-gradient(120deg, #172b4d, #28558a);
        color: #fff; padding: 24px 28px; border-radius: 18px; margin-bottom: 18px;
      }
      .hero h1 { color: #fff; margin: 0; font-size: 2rem; }
      .hero p { color: #e6edf8; margin: 7px 0 0 0; }
      .section-title {
        background: #28466d; color: #fff; padding: 10px 13px;
        border-radius: 10px; font-weight: 700; margin: 8px 0 12px 0;
      }
      .prob-card {
        border-radius: 11px; padding: 10px 12px; margin: 3px 0 8px 0;
        border: 1px solid rgba(20,40,70,.09); min-height: 69px;
      }
      .prob-label { font-size: .82rem; color: #334155; margin-bottom: 5px; }
      .prob-value { font-size: 1.34rem; font-weight: 800; }
      .green { background: #c6efce; color: #006100; }
      .yellow { background: #ffeb9c; color: #9c6500; }
      .red { background: #ffc7ce; color: #9c0006; }
      .neutral { background: #eef2f7; color: #334155; }
      .hint { color: #66758a; font-size: .88rem; }
      div[data-testid="stForm"] { background: white; padding: 18px; border: 1px solid #e3e9f2; border-radius: 15px; }
      div[data-testid="stMetric"] { background: white; border: 1px solid #e3e9f2; border-radius: 12px; padding: 12px; }
      .stButton button, .stFormSubmitButton button { border-radius: 9px; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>⚽ Futbol Tahmin Merkezi</h1>
      <p>Skor toplamlarını ve geçmiş sonuç sayılarını kendin gir; ilk yarı, ikinci yarı ve maç sonunu ayrı analiz et.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def poisson_distribution(lam: float, max_goals: int = MAX_GOALS) -> list[float]:
    """Poisson probability distribution, normalized over 0..max_goals."""
    lam = max(0.0, min(float(lam), 20.0))
    probs = [0.0] * (max_goals + 1)
    probs[0] = math.exp(-lam)
    for k in range(1, max_goals + 1):
        probs[k] = probs[k - 1] * lam / k
    total = sum(probs)
    if total <= 0:
        return [1.0] + [0.0] * max_goals
    return [p / total for p in probs]


def over_probability(p_a: list[float], p_b: list[float], minimum_total: int) -> float:
    return sum(
        p_a[a] * p_b[b]
        for a in range(len(p_a))
        for b in range(len(p_b))
        if a + b >= minimum_total
    )


def outcome_probabilities(p_a: list[float], p_b: list[float]) -> tuple[float, float, float]:
    home = draw = away = 0.0
    for a, pa in enumerate(p_a):
        for b, pb in enumerate(p_b):
            joint = pa * pb
            if a > b:
                home += joint
            elif a == b:
                draw += joint
            else:
                away += joint
    return home, draw, away


def top_scores(p_a: list[float], p_b: list[float], count: int = 5) -> list[tuple[str, float]]:
    scores: list[tuple[str, float]] = []
    for a, pa in enumerate(p_a):
        for b, pb in enumerate(p_b):
            scores.append((f"{a} - {b}", pa * pb))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores[:count]


def make_period_result(goals_a: int, goals_b: int, matches: int) -> dict[str, Any]:
    lam_a = goals_a / matches
    lam_b = goals_b / matches
    pa = poisson_distribution(lam_a)
    pb = poisson_distribution(lam_b)
    p1, px, p2 = outcome_probabilities(pa, pb)
    btts = (1 - pa[0]) * (1 - pb[0])
    return {
        "lambda_a": lam_a,
        "lambda_b": lam_b,
        "p1": p1,
        "px": px,
        "p2": p2,
        "1x": p1 + px,
        "x2": px + p2,
        "12": p1 + p2,
        "over05": over_probability(pa, pb, 1),
        "under05": 1 - over_probability(pa, pb, 1),
        "over15": over_probability(pa, pb, 2),
        "under15": 1 - over_probability(pa, pb, 2),
        "over25": over_probability(pa, pb, 3),
        "under25": 1 - over_probability(pa, pb, 3),
        "over35": over_probability(pa, pb, 4),
        "under35": 1 - over_probability(pa, pb, 4),
        "btts_yes": btts,
        "btts_no": 1 - btts,
        "scores": top_scores(pa, pb),
    }


def color_class(value: float) -> str:
    if value >= 0.60:
        return "green"
    if value >= 0.50:
        return "yellow"
    return "red"


def probability_card(label: str, value: float) -> None:
    cls = color_class(value)
    st.markdown(
        f"""<div class="prob-card {cls}">
          <div class="prob-label">{label}</div>
          <div class="prob-value">{value * 100:.1f}%</div>
        </div>""",
        unsafe_allow_html=True,
    )


def section_title(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def render_period(title: str, result: dict[str, Any], markets: tuple[str, str, str]) -> None:
    st.subheader(title)
    st.caption(
        f"Beklenen gol: A {result['lambda_a']:.2f} · B {result['lambda_b']:.2f} · "
        f"Toplam {result['lambda_a'] + result['lambda_b']:.2f}"
    )

    cols = st.columns(3)
    for col, (label, key) in zip(cols, [("1 · A kazanır", "p1"), ("X · Beraberlik", "px"), ("2 · B kazanır", "p2")]):
        with col:
            probability_card(label, result[key])

    cols = st.columns(3)
    for col, (label, key) in zip(cols, [("1X", "1x"), ("X2", "x2"), ("12", "12")]):
        with col:
            probability_card(label, result[key])

    st.markdown("**Alt / Üst**")
    over_keys = {
        "0,5": ("over05", "under05"),
        "1,5": ("over15", "under15"),
        "2,5": ("over25", "under25"),
        "3,5": ("over35", "under35"),
    }
    market_cols = st.columns(3)
    for col, line in zip(market_cols, markets):
        over_key, under_key = over_keys[line]
        with col:
            probability_card(f"{line} Üst", result[over_key])
            probability_card(f"{line} Alt", result[under_key])

    st.markdown("**Karşılıklı gol**")
    cols = st.columns(2)
    with cols[0]:
        probability_card("KG Var", result["btts_yes"])
    with cols[1]:
        probability_card("KG Yok", result["btts_no"])

    st.markdown("**En olası 5 skor**")
    score_cols = st.columns(5)
    for col, (score, probability) in zip(score_cols, result["scores"]):
        with col:
            probability_card(score, probability)


def clear_form() -> None:
    keys = [
        "team_a", "team_b", "match_count", "ht_a", "ht_b", "ft_a", "ft_b",
        "wins_a", "draws", "wins_b", "analysis_result", "analysis_error",
    ]
    for key in keys:
        st.session_state.pop(key, None)


if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "analysis_error" not in st.session_state:
    st.session_state.analysis_error = ""

input_col, result_col = st.columns([0.92, 1.75], gap="large")

with input_col:
    section_title("1. VERİ GİRİŞİ")
    st.markdown('<div class="hint">Maçları satır satır yazmana gerek yok. Toplam sayılarını girmen yeterli.</div>', unsafe_allow_html=True)

    with st.form("manual_football_data", clear_on_submit=False):
        team_a = st.text_input("Takım A (bu maçta ev sahibi)", key="team_a", placeholder="Örn. Galatasaray")
        team_b = st.text_input("Takım B (bu maçta deplasman)", key="team_b", placeholder="Örn. Fenerbahçe")
        match_count = st.number_input("İncelenen ikili maç sayısı", min_value=1, max_value=100, value=10, step=1, key="match_count")

        st.markdown("**İlk yarı toplam golleri**")
        ht_col_a, ht_col_b = st.columns(2)
        with ht_col_a:
            ht_a = st.number_input("A takımının golleri", min_value=0, max_value=2000, value=0, step=1, key="ht_a")
        with ht_col_b:
            ht_b = st.number_input("B takımının golleri", min_value=0, max_value=2000, value=0, step=1, key="ht_b")

        st.markdown("**Maç sonu toplam golleri**")
        ft_col_a, ft_col_b = st.columns(2)
        with ft_col_a:
            ft_a = st.number_input("A takımının golleri", min_value=0, max_value=2000, value=0, step=1, key="ft_a")
        with ft_col_b:
            ft_b = st.number_input("B takımının golleri", min_value=0, max_value=2000, value=0, step=1, key="ft_b")

        st.markdown("**Geçmiş maç sonuç sayıları (maç sonu)**")
        wins_col_a, draws_col, wins_col_b = st.columns(3)
        with wins_col_a:
            wins_a = st.number_input("A kazandı", min_value=0, max_value=100, value=0, step=1, key="wins_a")
        with draws_col:
            draws = st.number_input("Berabere", min_value=0, max_value=100, value=0, step=1, key="draws")
        with wins_col_b:
            wins_b = st.number_input("B kazandı", min_value=0, max_value=100, value=0, step=1, key="wins_b")

        submitted = st.form_submit_button("⚽ OLASILIKLARI HESAPLA", use_container_width=True, type="primary")

    st.button("GİRİŞLERİ TEMİZLE", on_click=clear_form, use_container_width=True)

    if submitted:
        errors = []
        clean_a = team_a.strip()
        clean_b = team_b.strip()
        n = int(match_count)

        if not clean_a or not clean_b:
            errors.append("İki takımın adını da yaz.")
        elif clean_a.casefold() == clean_b.casefold():
            errors.append("Takım A ve Takım B farklı olmalı.")

        if int(wins_a) + int(draws) + int(wins_b) != n:
            errors.append("A galibiyeti + beraberlik + B galibiyeti toplamı maç sayısına eşit olmalı.")

        if int(ht_a) > int(ft_a):
            errors.append("A takımının ilk yarı gol toplamı maç sonu gol toplamını aşamaz.")
        if int(ht_b) > int(ft_b):
            errors.append("B takımının ilk yarı gol toplamı maç sonu gol toplamını aşamaz.")

        if errors:
            st.session_state.analysis_result = None
            st.session_state.analysis_error = " ".join(errors)
        else:
            n = int(match_count)
            ht_result = make_period_result(int(ht_a), int(ht_b), n)
            second_result = make_period_result(int(ft_a) - int(ht_a), int(ft_b) - int(ht_b), n)
            full_result = make_period_result(int(ft_a), int(ft_b), n)

            # The manually entered historical full-time W/D/L counts are the primary
            # full-time 1X2 and double-chance values, as requested by the user.
            full_result["p1"] = int(wins_a) / n
            full_result["px"] = int(draws) / n
            full_result["p2"] = int(wins_b) / n
            full_result["1x"] = (int(wins_a) + int(draws)) / n
            full_result["x2"] = (int(draws) + int(wins_b)) / n
            full_result["12"] = (int(wins_a) + int(wins_b)) / n

            st.session_state.analysis_result = {
                "team_a": clean_a,
                "team_b": clean_b,
                "matches": n,
                "first_half": ht_result,
                "second_half": second_result,
                "full_time": full_result,
                "outcomes": {"A": int(wins_a), "X": int(draws), "B": int(wins_b)},
            }
            st.session_state.analysis_error = ""

with result_col:
    section_title("2. ANALİZ SONUÇLARI")

    if st.session_state.analysis_error:
        st.error(st.session_state.analysis_error)

    result = st.session_state.analysis_result
    if result is None:
        st.info("Sol taraftaki bilgileri doldurup **OLASILIKLARI HESAPLA** butonuna bas.")
        st.markdown(
            """
            <div class="prob-card neutral">
              <div class="prob-label">Renklerin anlamı</div>
              <div>🟩 %60 ve üzeri &nbsp; · &nbsp; 🟨 %50–59,9 &nbsp; · &nbsp; 🟥 %50'nin altı</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"### {result['team_a']} — {result['team_b']}")
        st.caption(f"Girilen ikili karşılaşma: {result['matches']} maç")

        outcome = result["outcomes"]
        c1, c2, c3 = st.columns(3)
        c1.metric("A galibiyeti", outcome["A"])
        c2.metric("Beraberlik", outcome["X"])
        c3.metric("B galibiyeti", outcome["B"])

        st.markdown("**Not:** Maç sonu 1-X-2 ve çifte şans yüzdeleri, girdiğin galibiyet/beraberlik sayılarından hesaplanır. Diğer pazarlar gol toplamlarının ortalamalarına dayalı Poisson modelidir.")
        st.caption("İlk yarı ve ikinci yarı sonuçları, ayrı skor toplamlarından tahmin edilir; tarih, saha rolü, güncel form, sakatlık ve bahis oranı kullanılmaz.")

        tab_ht, tab_2h, tab_ft = st.tabs(["İLK YARI", "İKİNCİ YARI", "MAÇ SONU"])
        with tab_ht:
            render_period("İlk Yarı Analizi", result["first_half"], ("0,5", "1,5", "2,5"))
        with tab_2h:
            render_period("İkinci Yarı Analizi", result["second_half"], ("0,5", "1,5", "2,5"))
        with tab_ft:
            render_period("Maç Sonu Analizi", result["full_time"], ("1,5", "2,5", "3,5"))

st.markdown("---")
st.caption(
    "Bu araç yalnızca elle girilen toplam verileri kullanır; dış kaynaktan veri çekmez. "
    "Tahminler istatistiksel tahminlerdir, kesin sonuç veya kârlılık garantisi değildir."
)
