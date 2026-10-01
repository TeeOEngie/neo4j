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
SIDEBAR_IMAGE = Path(__file__).parent / "image.png"

# ==================================================
# ตกแต่ง CSS
# ==================================================

st.markdown(
    """
    <style>
      .block-container {
        padding-top: 1.3rem;
        padding-bottom: 2rem;
      }

      .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 22px;
        background: linear-gradient(
          120deg,
          #111827 0%,
          #1f2937 55%,
          #0f766e 100%
        );
        color: white;
        margin-bottom: 1rem;
      }

      .hero h1 {
        margin: 0;
        font-size: 2.15rem;
      }

      .hero p {
        opacity: .88;
        margin: .35rem 0 0 0;
      }

      .monitor-card {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 16px;
        margin-bottom: .75rem;
      }

      .score-pill {
        display: inline-block;
        padding: .2rem .55rem;
        border-radius: 999px;
        background: #0f766e;
        color: white;
        font-size: .8rem;
        font-weight: 700;
      }

      .muted {
        opacity: .72;
        font-size: .9rem;
      }

      /* จัดรูปภาพในแถบด้านซ้ายให้มุมโค้ง */
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
            'password = "YOUR_PASSWORD"\n'
            'database = "neo4j"',
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
# อธิบายเหตุผลของคำแนะนำ
# ==================================================

def explain_reason(row: dict) -> str:
    parts = []

    if row.get("friend_count", 0):
        friends = ", ".join(row.get("friend_names") or [])
        parts.append(
            f"เพื่อน {row['friend_count']} คนชอบจอนี้"
            + (f" ({friends})" if friends else "")
        )

    if row.get("popularity", 0):
        parts.append(f"มีคนชอบทั้งหมด {row['popularity']} คน")

    return " • ".join(parts) or "แนะนำจากข้อมูลพฤติกรรมโดยรวม"


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

    # ถ้ามีไฟล์ monitor.png ให้แสดงรูป ถ้าไม่มีให้แสดงข้อความเตือน
    if SIDEBAR_IMAGE.is_file():
        st.image(str(SIDEBAR_IMAGE), caption="", width=120)
    else:
        st.info("กรุณาวางไฟล์ image.png ไว้ในโฟลเดอร์เดียวกับ app.py")


# ==================================================
# ส่วนหัวของเว็บไซต์
# ==================================================

st.markdown(
    """
    <div class="hero">
      <h1>🖥️ MonitorGraph Recommendation System</h1>
      <p>ระบบแนะนำจอคอมพิวเตอร์ด้วย Graph Database ที่อธิบายเหตุผลของคำแนะนำได้</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 1. Dashboard
# ==================================================

if page == "Dashboard":

    st.subheader("ภาพรวมระบบ")

    m = get_dashboard_metrics()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Users", m.get("users", 0))
    c2.metric("Monitors", m.get("monitors", 0))
    c3.metric("Like relationships", m.get("likes", 0))
    c4.metric("Friend relationships", m.get("friendships", 0))

    st.divider()

    user_id = user_selector("dash_user")
    profile = get_profile(user_id)

    if profile:

        left, right = st.columns([1, 2])

        with left:
            st.markdown(f"### {profile['name']}")
            st.write(f"**รหัส:** {profile['user_id']}")
            st.write(
                "**เพื่อน:** "
                + (", ".join(profile["friends"]) or "ยังไม่มี")
            )

        with right:
            st.markdown("### จอที่ชอบ")

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

    user_id = user_selector("rec_user")

    top_n = st.slider("จำนวนคำแนะนำ", 3, 12, 6)

    rows = recommend_monitors(user_id, top_n)

    st.caption(
        "คะแนน = จำนวนเพื่อนที่ชอบจอนี้ "
        "(ถ้าคะแนนเท่ากัน จอที่มีคนชอบมากกว่าจะขึ้นก่อน)"
    )

    if not rows:
        st.info("ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้")

    for i, row in enumerate(rows, start=1):

        # การ์ดแสดงจอที่แนะนำ 1 รุ่น
        st.markdown(
            f"""
            <div class="monitor-card">
              <span class="score-pill">#{i} · score {row['score']}</span>
              <h3 style="margin:.55rem 0 .2rem 0">{row['name']}</h3>
              <div class="muted">{row['monitor_id']}</div>
              <p><b>เหตุผล:</b> {explain_reason(row)}</p>
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

    st.write(f"พบ {len(rows)} รายการ")

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

    if st.button("กดชอบ", type="primary", use_container_width=True):

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
            'node [shape=box, style="rounded,filled", fillcolor="#f8fafc"];',
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
                    dot.append(f'"{nid}" [label="{safe_name}\\n:{label}"];')
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