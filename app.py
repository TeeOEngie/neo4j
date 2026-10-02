from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from neo4j_service import (
    add_friendship,
    add_user,
    delete_user,
    get_dashboard_metrics,
    get_profile,
    get_users,
    graph_neighborhood,
    ping,
    recommend_monitors,
    search_monitors,
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
      .stButton > button[kind="primary"],
      [data-testid="stFormSubmitButton"] > button {
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

      /* ===== เมนู sidebar แบบไม่มีวงกลม ===== */
      [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
        display: none;                 /* ซ่อนวงกลมติ๊ก */
      }

      [data-testid="stSidebar"] [role="radiogroup"] > label {
        width: 100%;
        padding: .6rem .9rem;
        margin-bottom: .3rem;
        border-radius: 12px;
        cursor: pointer;
        transition: background .2s;
      }

      [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
        background: rgba(8,145,178,.12);   /* เอาเมาส์ชี้แล้วมีสีจาง ๆ */
      }

      [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(90deg, #06b6d4, #6366f1);   /* เมนูที่เลือกอยู่ */
      }

      [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
        color: white;
        font-weight: 600;
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

def user_selector(key: str = "user", label: str = "เลือกผู้ใช้") -> str:
    users = get_users()

    if not users:
        st.info("ยังไม่มีข้อมูลผู้ใช้ กรุณาไปหน้า Manage Data แล้วเพิ่มคนก่อน")
        st.stop()

    # สร้างรายการให้เลือก เช่น "U001 — Tony"
    labels = {
        f"{x['user_id']} — {x['name']}": x["user_id"]
        for x in users
    }

    chosen = st.selectbox(label, list(labels), key=key)

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

    # ไอคอนหน้าเมนู (ชื่อหน้าข้างในยังเหมือนเดิม)
    menu_icons = {
        "Dashboard": "📊  Dashboard",
        "Recommendations": "✨  Recommendations",
        "Monitor Search": "🔎  Monitor Search",
        "Graph Explorer": "🕸️  Graph Explorer",
        "Manage Data": "🛠️  Manage Data",
    }

    # เมนูหลักของระบบ
    page = st.radio(
        "เมนู",
        list(menu_icons),
        format_func=lambda p: menu_icons[p],   # แสดงชื่อพร้อมไอคอน
        label_visibility="collapsed",          # ซ่อนคำว่า "เมนู"
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
# 4. Graph Explorer
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
# 5. Manage Data (เพิ่มคน + เพิ่มความสัมพันธ์ + ลบคน)
# ==================================================

elif page == "Manage Data":

    st.subheader("🛠️ จัดการข้อมูล")

    # แสดงข้อความที่ค้างไว้จากรอบก่อน (ใช้ตอนลบคนแล้วรีเฟรชหน้า)
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

    tab_user, tab_friend, tab_delete = st.tabs(
        ["👤 เพิ่มคน", "🤝 เพิ่มความสัมพันธ์เพื่อน", "🗑️ ลบคน"]
    )

    # ---------- แท็บเพิ่มคน ----------
    with tab_user:

        # form = กดปุ่มแล้วค่อยส่งข้อมูล และล้างช่องกรอกให้อัตโนมัติ
        with st.form("add_user_form", clear_on_submit=True):
            name = st.text_input("ชื่อ", placeholder="เช่น Peter")
            submitted = st.form_submit_button("➕ เพิ่มคน", use_container_width=True)

        if submitted:
            if not name.strip():
                st.warning("กรุณากรอกชื่อ")
            else:
                new_id = add_user(name)
                st.success(f"เพิ่ม {name.strip()} สำเร็จ รหัส {new_id}")

        # แสดงรายชื่อทั้งหมดใต้ฟอร์ม
        st.markdown("#### รายชื่อทั้งหมด")
        st.dataframe(
            pd.DataFrame(get_users()),
            use_container_width=True,
            hide_index=True,
        )

    # ---------- แท็บเพิ่มเพื่อน ----------
    with tab_friend:

        c1, c2 = st.columns(2)

        with c1:
            user1 = user_selector("friend_user1", "คนที่ 1")

        with c2:
            user2 = user_selector("friend_user2", "คนที่ 2")

        if st.button("🤝 เป็นเพื่อนกัน", type="primary", use_container_width=True):

            if user1 == user2:
                st.warning("เลือกคนเดียวกันไม่ได้ กรุณาเลือกคนละคน")
            elif add_friendship(user1, user2):
                st.success(f"{user1} กับ {user2} เป็นเพื่อนกันแล้ว")
            else:
                st.info("สองคนนี้เป็นเพื่อนกันอยู่แล้ว")

        # แสดงเพื่อนปัจจุบันของคนที่ 1
        profile = get_profile(user1)

        if profile:
            chips = friend_chips(profile["friends"]) or '<span class="muted">ยังไม่มีเพื่อน</span>'
            st.markdown(
                f"""
                <p style="margin:1rem 0 .4rem 0"><b>เพื่อนของ {profile['name']} ตอนนี้</b></p>
                <div class="chips">{chips}</div>
                """,
                unsafe_allow_html=True,
            )

    # ---------- แท็บลบคน ----------
    with tab_delete:

        del_id = user_selector("delete_user", "เลือกคนที่จะลบ")
        target = get_profile(del_id)

        if target:
            st.warning(
                f"จะลบ **{target['name']} ({target['user_id']})** "
                f"พร้อมเพื่อน {len(target['friends'])} เส้น "
                f"และจอที่ชอบ {len(target['liked'])} เส้น ลบแล้วกู้คืนไม่ได้"
            )

            # ต้องติ๊กยืนยันก่อน ปุ่มลบถึงจะกดได้
            confirm = st.checkbox("ยืนยันว่าต้องการลบจริง", key="confirm_delete")

            if st.button("🗑️ ลบคนนี้", type="primary", use_container_width=True, disabled=not confirm):

                delete_user(del_id)

                # เก็บข้อความไว้ แล้วรีเฟรชหน้าให้รายชื่ออัปเดต
                st.session_state["flash"] = f"ลบ {target['name']} ({del_id}) เรียบร้อยแล้ว"
                st.session_state.pop("confirm_delete", None)
                st.rerun()