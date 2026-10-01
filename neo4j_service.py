from __future__ import annotations

import streamlit as st
from neo4j import GraphDatabase


# ==================================================
# เชื่อมต่อ Neo4j (สร้าง driver ครั้งเดียว แล้วใช้ซ้ำ)
# ==================================================

@st.cache_resource
def get_driver():
    cfg = st.secrets["neo4j"]
    return GraphDatabase.driver(
        cfg["uri"],
        auth=(cfg["username"], cfg["password"]),
    )


def _database() -> str:
    # ถ้าไม่ได้ใส่ database ใน secrets ให้ใช้ "neo4j"
    return st.secrets["neo4j"].get("database", "neo4j")


def run(query: str, **params) -> list[dict]:
    # รัน Cypher แล้วแปลงผลเป็น list ของ dict
    records, _, _ = get_driver().execute_query(
        query,
        database_=_database(),
        **params,
    )
    return [r.data() for r in records]


# ==================================================
# เช็กว่าเชื่อมต่อได้
# ==================================================

def ping() -> bool:
    rows = run("RETURN 1 AS ok")
    return bool(rows) and rows[0]["ok"] == 1


# ==================================================
# รายชื่อผู้ใช้ทั้งหมด
# ==================================================

def get_users() -> list[dict]:
    return run(
        """
        MATCH (u:User)
        RETURN u.user_id AS user_id, u.name AS name
        ORDER BY user_id
        """
    )


# ==================================================
# ตัวเลขภาพรวมสำหรับ Dashboard
# ==================================================

def get_dashboard_metrics() -> dict:
    rows = run(
        """
        CALL { MATCH (u:User) RETURN count(u) AS users }
        CALL { MATCH (m:Monitor) RETURN count(m) AS monitors }
        CALL { MATCH (:User)-[r:LIKES]->(:Monitor) RETURN count(r) AS likes }
        CALL { MATCH (:User)-[f:FRIEND_OF]->(:User) RETURN count(f) AS friendships }
        RETURN users, monitors, likes, friendships
        """
    )
    return rows[0] if rows else {}


# ==================================================
# โปรไฟล์ผู้ใช้: ชื่อ เพื่อน และจอที่ชอบ
# ==================================================

def get_profile(user_id: str) -> dict | None:
    rows = run(
        """
        MATCH (u:User {user_id: $user_id})

        // เพื่อนทั้งสองทิศ
        OPTIONAL MATCH (u)-[:FRIEND_OF]-(f:User)
        WITH u, collect(DISTINCT f.name) AS friends

        // จอที่ชอบ (ถ้าไม่มี collect จะข้าม null ให้เอง)
        OPTIONAL MATCH (u)-[:LIKES]->(m:Monitor)
        WITH u, friends,
             collect(
                 CASE WHEN m IS NULL THEN null
                      ELSE {monitor_id: m.monitor_id, name: m.name}
                 END
             ) AS liked

        RETURN u.user_id AS user_id,
               u.name AS name,
               friends,
               liked
        """,
        user_id=user_id,
    )

    if not rows:
        return None

    profile = rows[0]
    profile["friends"] = sorted(profile["friends"])
    profile["liked"] = sorted(profile["liked"], key=lambda x: x["monitor_id"])
    return profile


# ==================================================
# แนะนำจอจากเพื่อน (แบบเดียวกับ Step 19)
# ==================================================

def recommend_monitors(user_id: str, top_n: int = 6) -> list[dict]:
    return run(
        """
        MATCH (me:User {user_id: $user_id})
              -[:FRIEND_OF]-(friend:User)
              -[:LIKES]->(m:Monitor)

        // ตัดจอที่ตัวเองชอบอยู่แล้ว
        WHERE NOT EXISTS { MATCH (me)-[:LIKES]->(m) }

        WITH m, collect(DISTINCT friend.name) AS friend_names

        // นับว่าทั้งระบบมีคนชอบจอนี้กี่คน ใช้เป็นตัวตัดสินตอนคะแนนเท่ากัน
        OPTIONAL MATCH (:User)-[l:LIKES]->(m)
        WITH m, friend_names, count(l) AS popularity

        RETURN m.monitor_id AS monitor_id,
               m.name AS name,
               size(friend_names) AS friend_count,
               friend_names,
               popularity,
               size(friend_names) AS score

        ORDER BY score DESC, popularity DESC, name
        LIMIT $top_n
        """,
        user_id=user_id,
        top_n=top_n,
    )


# ==================================================
# ค้นหาจอจากชื่อ
# ==================================================

def search_monitors(keyword: str = "") -> list[dict]:
    return run(
        """
        MATCH (m:Monitor)
        WHERE $keyword = ""
           OR toLower(m.name) CONTAINS toLower($keyword)

        OPTIONAL MATCH (:User)-[l:LIKES]->(m)

        RETURN m.monitor_id AS monitor_id,
               m.name AS name,
               count(l) AS likes
        ORDER BY monitor_id
        """,
        keyword=keyword.strip(),
    )


# ==================================================
# บันทึกการกดชอบ
# ==================================================

def record_like(user_id: str, monitor_id: str) -> None:
    run(
        """
        MATCH (u:User {user_id: $user_id})
        MATCH (m:Monitor {monitor_id: $monitor_id})
        MERGE (u)-[:LIKES]->(m)   // กดซ้ำก็ไม่สร้างเส้นซ้ำ
        """,
        user_id=user_id,
        monitor_id=monitor_id,
    )


# ==================================================
# ข้อมูลกราฟรอบตัวผู้ใช้ (ใช้วาดใน Graph Explorer)
# ==================================================

def graph_neighborhood(user_id: str) -> list[dict]:
    return run(
        """
        MATCH (me:User {user_id: $user_id})

        CALL (me) {
            // 1) ผู้ใช้ -> เพื่อน
            MATCH (me)-[:FRIEND_OF]-(f:User)
            RETURN me.user_id AS source_id, 'User' AS source_label, me.name AS source_name,
                   'FRIEND_OF' AS relationship,
                   f.user_id AS target_id, 'User' AS target_label, f.name AS target_name

            UNION

            // 2) ผู้ใช้ -> จอที่ชอบ
            MATCH (me)-[:LIKES]->(m:Monitor)
            RETURN me.user_id AS source_id, 'User' AS source_label, me.name AS source_name,
                   'LIKES' AS relationship,
                   m.monitor_id AS target_id, 'Monitor' AS target_label, m.name AS target_name

            UNION

            // 3) เพื่อน -> จอที่เพื่อนชอบ
            MATCH (me)-[:FRIEND_OF]-(f:User)-[:LIKES]->(m:Monitor)
            RETURN f.user_id AS source_id, 'User' AS source_label, f.name AS source_name,
                   'LIKES' AS relationship,
                   m.monitor_id AS target_id, 'Monitor' AS target_label, m.name AS target_name
        }

        RETURN source_id, source_label, source_name,
               relationship,
               target_id, target_label, target_name
        """,
        user_id=user_id,
    )


# ==================================================
# ข้อมูลตัวอย่าง (ชุดเดียวกับใน Colab)
# ==================================================

USERS = [
    {"user_id": "U001", "name": "Tony"},
    {"user_id": "U002", "name": "Jame"},
    {"user_id": "U003", "name": "Jack"},
    {"user_id": "U004", "name": "Ben"},
    {"user_id": "U005", "name": "Smit"},
    {"user_id": "U006", "name": "Joseph"},
    {"user_id": "U007", "name": "Henry"},
    {"user_id": "U008", "name": "Harry"},
    {"user_id": "U009", "name": "Jonathan"},
    {"user_id": "U010", "name": "Mark"},
]

MONITORS = [
    {"monitor_id": "M001", "name": "ASUS ROG Swift PG279QM"},
    {"monitor_id": "M002", "name": "Samsung Odyssey G9"},
    {"monitor_id": "M003", "name": "LG UltraGear 27GP850"},
    {"monitor_id": "M004", "name": "Acer Predator X34"},
    {"monitor_id": "M005", "name": "MSI Optix MAG274QRF"},
    {"monitor_id": "M006", "name": "AOC 24G2"},
    {"monitor_id": "M007", "name": "ViewSonic VX2458"},
    {"monitor_id": "M008", "name": "Gigabyte M27Q"},
    {"monitor_id": "M009", "name": "Acer Nitro VG240Y"},
    {"monitor_id": "M010", "name": "Dell S3422DWG"},
    {"monitor_id": "M011", "name": "Dell UltraSharp U2723QE"},
    {"monitor_id": "M012", "name": "BenQ PD2700U"},
    {"monitor_id": "M013", "name": "LG UltraFine 27UP850"},
    {"monitor_id": "M014", "name": "ASUS ProArt PA278CV"},
    {"monitor_id": "M015", "name": "Eizo ColorEdge CS2731"},
    {"monitor_id": "M016", "name": "Dell P2422H"},
    {"monitor_id": "M017", "name": "HP E24 G4"},
    {"monitor_id": "M018", "name": "Lenovo ThinkVision P27h-20"},
    {"monitor_id": "M019", "name": "Samsung Smart Monitor M8"},
    {"monitor_id": "M020", "name": "LG 34WN80C"},
]

FRIENDSHIPS = [
    {"user1": "U001", "user2": "U005"},
    {"user1": "U001", "user2": "U007"},
    {"user1": "U002", "user2": "U003"},
    {"user1": "U003", "user2": "U008"},
    {"user1": "U004", "user2": "U006"},
    {"user1": "U004", "user2": "U009"},
    {"user1": "U006", "user2": "U009"},
    {"user1": "U007", "user2": "U010"},
    {"user1": "U002", "user2": "U007"},
    {"user1": "U006", "user2": "U010"},
]

# (user_id, monitor_id) แต่ละคนชอบ 3 จอ
LIKES = [
    ("U001", "M011"), ("U001", "M012"), ("U001", "M014"),
    ("U002", "M001"), ("U002", "M002"), ("U002", "M003"),
    ("U003", "M003"), ("U003", "M009"), ("U003", "M005"),
    ("U004", "M016"), ("U004", "M017"), ("U004", "M018"),
    ("U005", "M012"), ("U005", "M015"), ("U005", "M013"),
    ("U006", "M016"), ("U006", "M019"), ("U006", "M018"),
    ("U007", "M001"), ("U007", "M011"), ("U007", "M020"),
    ("U008", "M009"), ("U008", "M006"), ("U008", "M007"),
    ("U009", "M016"), ("U009", "M017"), ("U009", "M018"),
    ("U010", "M020"), ("U010", "M019"), ("U010", "M011"),
]


def seed_demo_data() -> None:
    # Constraint ต้องรันทีละคำสั่ง
    run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
    run("CREATE CONSTRAINT monitor_id_unique IF NOT EXISTS FOR (m:Monitor) REQUIRE m.monitor_id IS UNIQUE")

    # Users
    run(
        """
        UNWIND $rows AS row
        MERGE (u:User {user_id: row.user_id})
        SET u.name = row.name
        """,
        rows=USERS,
    )

    # Monitors
    run(
        """
        UNWIND $rows AS row
        MERGE (m:Monitor {monitor_id: row.monitor_id})
        SET m.name = row.name
        """,
        rows=MONITORS,
    )

    # FRIEND_OF
    run(
        """
        UNWIND $rows AS row
        MATCH (a:User {user_id: row.user1})
        MATCH (b:User {user_id: row.user2})
        MERGE (a)-[:FRIEND_OF]->(b)
        """,
        rows=FRIENDSHIPS,
    )

    # LIKES
    run(
        """
        UNWIND $rows AS row
        MATCH (u:User {user_id: row.user_id})
        MATCH (m:Monitor {monitor_id: row.monitor_id})
        MERGE (u)-[:LIKES]->(m)
        """,
        rows=[{"user_id": u, "monitor_id": m} for u, m in LIKES],
    )