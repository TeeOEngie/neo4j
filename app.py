from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from neo4j_service import (
    get_dashboard_metrics,
    get_profile,
    get_users,
    graph_neighborhood,
    ping,
    recommend_monitors,
    record_like,
    search_monitors,
    seed_demo_data,
)

# ==================================================
# ตั้งค่าหน้าเว็บ
# ==================================================

st.set_page_config(
    page_title="MonitorGraph Recommender",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ตำแหน่งไฟล์รูปภาพ อยู่โฟลเดอร์เดียวกับ app.py
SIDEBAR_IMAGE = Path(__file__).parent / "library.png"

# ==================================================
# ตกแต่ง CSS
# ==================================================

st.markdown(
    """
    <style>
      /* ฟอนต์ภาษาไทย Prompt */
      @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap');

      html, body, p, h1, h2, h3, h4, label, li {
        font-family: 'Prompt', sans-serif !important;
      }

      .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
      }

      /* ===== Hero ด้านบน ===== */
      .hero {
        padding: 2rem 2.2rem;
        border-radius: 24px;
        background:
          radial-gradient(circle at 85% 20%, rgba(34,211,238,.35), transparent 45%),
          radial-gradient(circle at 10% 90%, rgba(99,102,241,.35), transparent 40%),
          linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        box-shadow: 0 10px 30px rgba(15,23,42,.25);
        margin-bottom: 1.5rem;
      }

      .hero-badge {
        display: inline-block;
        padding: .25rem .75rem;
        border-radius: 999px;
        background: rgba(34,211,238,.18);
        color: #67e8f9;
        font-size: .8rem;
        font-weight: 600;
        margin-bottom: .6rem;
      }

      .hero h1 {
        margin: 0;
        font-size: 2.4rem;
        font-weight: 700;
        color: #f8fafc;
      }

      .hero p {
        margin: .4rem 0 0 0;
        color: #cbd5e1;
        font-size: 1.05rem;
      }

      /* ===== กล่องตัวเลข Dashboard ===== */
      [data-testid="stMetric"] {
        background: rgba(8,145,178,.07);
        border: 1px solid rgba(8,145,178,.25);
        border-radius: 18px;
        padding: 1rem 1.2rem;
      }

      [data-testid="stMetricValue"] {
        color: #0891b2;
        font-weight: 700;
      }

      /* ===== การ์ดจอที่แนะนำ ===== */
      .monitor-card {
        padding: 1.1rem 1.3rem;
        border-radius: 18px;
        background: rgba(148,163,184,.08);
        border: 1px solid rgba(148,163,184,.25);
        margin-bottom: .9rem;
        transition: border-color .2s, transform .2s;
      }

      .monitor-card:hover {
        border-color: rgba(8,145,178,.6);
        transform: translateY(-2px);
      }

      .card-top {
        display: flex;
        align-items: center;
        gap: 1rem;
      }

      .rank {
        flex: 0 0 auto;
        width: 46px;
        height: 46px;
        border-radius: 14px;
        display: grid;
        place-items: center;
        font-weight: 700;
        color: white;
        background: linear-gradient(135deg, #06b6d4, #6366f1);
      }

      .card-title {
        flex: 1;
        min-width: 0;
      }

      .card-title h3 {
        margin: 0;
        font-size: 1.15rem;
      }

      .score {
        text-align: right;
        font-size: 1.6rem;
        font-weight: 700;
        color: #0891b2;
        line-height: 1;
      }

      .score small {
        display: block;
        font-size: .7rem;
        opacity: .7;
        font-weight: 500;
      }

      /* แถบคะแนน */
      .bar {
        height: 6px;
        border-radius: 999px;
        background: rgba(148,163,184,.2);
        margin: .9rem 0 .7rem 0;
        overflow: hidden;
      }

      .bar > div {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #06b6d4, #6366f1);
      }

      /* ป้ายชื่อเพื่อน */
      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: .4rem;
      }

      .chip {
        padding: .2rem .65rem;
        border-radius: 999px;
        background: rgba(99,102,241,.15);
        color: #6366f1;
        font-size: .82rem;
        font-weight: 500;
      }

      .muted {
        opacity: .7;
        font-size: .88rem;
      }

      /* ===== การ์ดโปรไฟล์ ===== */
      .profile-card {
        padding: 1.3rem;
        border-radius: 18px;
        background: rgba(8,145,178,.07);
        border: 1px solid rgba(8,145,178,.25);
      }

      .avatar {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        font-size: 1.6rem;
        font-weight: 700;
        color: white;
        background: linear-gradient(135deg, #06b6d4, #6366f1);
        margin-bottom: .7rem;
      }

      /* ===== ปุ่มหลัก ===== */
      .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #06b6d4, #6366f1);
        border: none;
        color: white;
        font-weight: 700;
        border-radius: 12px;
      }

      /* รูปใน sidebar มุมโค้ง */
      [data-testid="stSidebar"] img {
        border-radius: 14px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# ตรวจสอบการเชื่อมต่อ Neo4j
# ==================================================

def require_connection() -> None:
    try:
        if not ping():
            raise RuntimeError("Neo4j did not return a healthy response")

    except Exception as exc:
        st.error("ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ")

        st.code(
            '[neo4j]\n'
            'uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"\n'
            'username = "neo4j"\n'
            'password = "YOUR_PASSWORD"',
            language="toml",
        )

        st.caption(
            "ให้นำค่าด้านบนไปใส่ใน Streamlit Secrets "
            "และห้าม commit password ลง GitHub"
        )

        st.exception(exc)
        st.stop()


# ==================================================
# เลือกผู้ใช้
# ==================================================

def user_selector(key: str = "user") -> str:
    users = get_users()

    if not users:
        st.info(
            "ยังไม่มีข้อมูลผู้ใช้ "
            "กรุณาไปหน้า Admin / Setup "
            "แล้วสร้างข้อมูลตัวอย่าง"
        )
        st.stop()

    # สร้างรายการให้เลือก เช่น "U001 — Tony"
    labels = {
        f"{x['user_id']} — {x['name']}": x["user_id"]
        for x in users
    }

    chosen = st.selectbox("เลือกผู้ใช้", list(labels), key=key)

    return labels[chosen]


# ==================================================
# สร้างป้ายชื่อเพื่อน (ใช้ทั้งหน้า Dashboard และ Recommendations)
# ==================================================

def friend_chips(names: list[str]) -> str:
    return "".join(f'<span class="chip">👤 {n}</span>' for n in names)


# ==================================================
# เริ่มต้นระบบ
# ==================================================

require_connection()


# ==================================================
# แถบเมนูด้านซ้าย (Sidebar)
# ==================================================

with st.sidebar:

    st.markdown("## 🖥️ MonitorGraph")
    st.caption("Neo4j Aura + Streamlit")

    # เมนูหลักของระบบ
    page = st.radio(
        "เมนู",
        [
            "Dashboard",
            "Recommendations",
            "Monitor Search",
            "Like Monitor",
            "Graph Explorer",
            "Admin / Setup",
        ],
    )

    st.divider()

    st.caption("Bachelor-level Graph Database Project")

    st.markdown("<br>", unsafe_allow_html=True)

    # ถ้ามีไฟล์รูปให้แสดง ถ้าไม่มีให้แสดงข้อความเตือน
    if SIDEBAR_IMAGE.is_file():
        st.image(str(SIDEBAR_IMAGE), caption="", width=120)
    else:
        st.info("กรุณาวางไฟล์ library.png ไว้ในโฟลเดอร์เดียวกับ app.py")


# ==================================================
# ส่วนหัวของเว็บไซต์
# ==================================================

st.markdown(
    """
    <div class="hero">
      <div class="hero-badge">Neo4j Aura · Streamlit</div>
      <h1>🖥️ MonitorGraph</h1>
      <p>ระบบแนะนำจอคอมพิวเตอร์จากความชอบของเพื่อน ด้วย Graph Database</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 1. Dashboard
# ==================================================

if page == "Dashboard":

    st.subheader("📊 ภาพรวมระบบ")

    m = get_dashboard_metrics()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 Users", m.get("users", 0))
    c2.metric("🖥️ Monitors", m.get("monitors", 0))
    c3.metric("👍 Likes", m.get("likes", 0))
    c4.metric("🤝 Friends", m.get("friendships", 0))

    st.divider()

    user_id = user_selector("dash_user")
    profile = get_profile(user_id)

    if profile:

        left, right = st.columns([1, 2])

        with left:
            chips = friend_chips(profile["friends"]) or '<span class="muted">ยังไม่มีเพื่อน</span>'

            # การ์ดโปรไฟล์: ตัวอักษรแรกของชื่อ + ชื่อ + รหัส + เพื่อน
            st.markdown(
                f"""
                <div class="profile-card">
                  <div class="avatar">{profile['name'][0]}</div>
                  <h3 style="margin:0">{profile['name']}</h3>
                  <div class="muted">{profile['user_id']}</div>
                  <p style="margin:.9rem 0 .4rem 0"><b>เพื่อน</b></p>
                  <div class="chips">{chips}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            st.markdown("### 🖥️ จอที่ชอบ")

            if profile["liked"]:
                st.dataframe(
                    pd.DataFrame(profile["liked"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("ยังไม่ได้กดชอบจอใดเลย")


# ==================================================
# 2. Recommendations
# ==================================================

elif page == "Recommendations":

    st.subheader("✨ จอที่แนะนำ")

    c1, c2 = st.columns([2, 1])

    with c1:
        user_id = user_selector("rec_user")

    with c2:
        top_n = st.slider("จำนวนคำแนะนำ", 3, 12, 6)

    rows = recommend_monitors(user_id, top_n)

    st.caption(
        "คะแนน = จำนวนเพื่อนที่ชอบจอนี้ "
        "(ถ้าคะแนนเท่ากัน จอที่มีคนชอบมากกว่าจะขึ้นก่อน)"
    )

    if not rows:
        st.info("ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้")

    # คะแนนสูงสุด ใช้คำนวณความยาวแถบ
    max_score = max((r["score"] for r in rows), default=1)

    for i, row in enumerate(rows, start=1):

        pct = int(row["score"] / max_score * 100)   # ความยาวแถบเป็น %

        # การ์ดแสดงจอที่แนะนำ 1 รุ่น
        st.markdown(
            f"""
            <div class="monitor-card">
              <div class="card-top">
                <div class="rank">#{i}</div>
                <div class="card-title">
                  <h3>{row['name']}</h3>
                  <div class="muted">{row['monitor_id']} · มีคนชอบทั้งหมด {row['popularity']} คน</div>
                </div>
                <div class="score">{row['score']}<small>คะแนน</small></div>
              </div>
              <div class="bar"><div style="width:{pct}%"></div></div>
              <div class="chips">{friend_chips(row.get('friend_names') or [])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==================================================
# 3. Monitor Search
# ==================================================

elif page == "Monitor Search":

    st.subheader("🔎 ค้นหาจอ")

    keyword = st.text_input(
        "ชื่อจอหรือยี่ห้อ",
        placeholder="เช่น Dell, LG, ASUS",
    )

    rows = search_monitors(keyword)

    st.write(f"พบ **{len(rows)}** รายการ")

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


# ==================================================
# 4. Like Monitor
# ==================================================

elif page == "Like Monitor":

    st.subheader("👍 บันทึกการกดชอบ")

    user_id = user_selector("like_user")

    monitors = search_monitors()

    if not monitors:
        st.info("ยังไม่มีข้อมูลจอ")
        st.stop()

    monitor_labels = {
        f"{m['monitor_id']} — {m['name']}": m["monitor_id"]
        for m in monitors
    }

    selected = st.selectbox("จอ", list(monitor_labels))

    if st.button("👍 กดชอบ", type="primary", use_container_width=True):

        # บันทึกความสัมพันธ์ LIKES ลง Neo4j
        record_like(user_id, monitor_labels[selected])

        st.success("บันทึกความสัมพันธ์ LIKES แล้ว")


# ==================================================
# 5. Graph Explorer
# ==================================================

elif page == "Graph Explorer":

    st.subheader("🕸️ Graph Explorer")

    user_id = user_selector("graph_user")

    rows = graph_neighborhood(user_id)

    if not rows:
        st.info("ยังไม่มี neighborhood graph")

    else:
        # สร้างกราฟด้วยภาษา DOT ของ Graphviz
        dot = [
            "digraph G {",
            'rankdir="LR";',
            'bgcolor="transparent";',
            'node [shape=box, style="rounded,filled", fontcolor="#0f172a", color="none", fontname="Helvetica"];',
            'edge [color="#64748b", fontcolor="#64748b", fontsize=10];',
        ]

        seen_nodes = set()

        for r in rows:

            for nid, label, name in [
                (r["source_id"], r["source_label"], r["source_name"]),
                (r["target_id"], r["target_label"], r["target_name"]),
            ]:
                # เพิ่มโหนดแค่ครั้งเดียว ไม่ให้ซ้ำ
                if nid not in seen_nodes:
                    safe_name = str(name).replace('"', "'")
                    # User สีฟ้า, Monitor สีม่วง
                    fill = "#67e8f9" if label == "User" else "#a5b4fc"
                    dot.append(f'"{nid}" [label="{safe_name}\\n:{label}", fillcolor="{fill}"];')
                    seen_nodes.add(nid)

            # เพิ่มเส้นเชื่อมระหว่างโหนด
            dot.append(
                f'"{r["source_id"]}" -> "{r["target_id"]}" '
                f'[label="{r["relationship"]}"];'
            )

        dot.append("}")

        st.graphviz_chart("\n".join(dot), use_container_width=True)

        with st.expander("ดูข้อมูล edge ที่ใช้วาดกราฟ"):
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )


# ==================================================
# 6. Admin / Setup
# ==================================================

elif page == "Admin / Setup":

    st.subheader("⚙️ Setup ข้อมูลตัวอย่าง")

    st.warning("ปุ่มนี้ไม่ลบข้อมูลเดิม และใช้ MERGE จึงสามารถกดซ้ำได้")

    st.markdown(
        """
        **Graph schema**

        - `(:User)-[:FRIEND_OF]-(:User)`
        - `(:User)-[:LIKES]->(:Monitor)`
        """
    )

    if st.button("สร้าง Constraint + Demo Data", type="primary", use_container_width=True):

        with st.spinner("กำลังสร้างข้อมูล..."):
            seed_demo_data()

        st.success("สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว")
        st.rerun()