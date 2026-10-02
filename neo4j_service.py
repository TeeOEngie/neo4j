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
    # ใส่ชื่อ database ของ Aura ตรงนี้ (ค่าเดียวกับ DATABASE ใน Colab)
    return "c2f5effc"


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
# แนะนำจอจากเพื่อน
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

        // นับว่าทั้งระบบมีคนชอบจอนี้กี่คน ใช้ตัดสินตอนคะแนนเท่ากัน
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
# หารหัส user ถัดไป เช่น มีถึง U010 จะได้ U011
# ==================================================

def next_user_id() -> str:
    rows = run(
        """
        MATCH (u:User)
        WHERE u.user_id STARTS WITH 'U'
        RETURN max(toInteger(substring(u.user_id, 1))) AS n
        """
    )
    n = rows[0]["n"] or 0
    return f"U{n + 1:03d}"   # เติม 0 ข้างหน้าให้ครบ 3 หลัก


# ==================================================
# เพิ่มคนใหม่
# ==================================================

def add_user(name: str) -> str:
    user_id = next_user_id()
    run(
        "CREATE (u:User {user_id: $user_id, name: $name})",
        user_id=user_id,
        name=name.strip(),
    )
    return user_id


# ==================================================
# เพิ่มความสัมพันธ์เพื่อน (คืนค่า False ถ้าเป็นเพื่อนกันอยู่แล้ว)
# ==================================================

def add_friendship(user1: str, user2: str) -> bool:
    rows = run(
        """
        MATCH (a:User {user_id: $user1})
        MATCH (b:User {user_id: $user2})

        // สร้างเฉพาะถ้ายังไม่เป็นเพื่อนกัน (เช็กทั้งสองทิศ)
        WHERE NOT EXISTS { MATCH (a)-[:FRIEND_OF]-(b) }

        CREATE (a)-[:FRIEND_OF]->(b)
        RETURN count(*) AS created
        """,
        user1=user1,
        user2=user2,
    )
    return bool(rows) and rows[0]["created"] > 0


# ==================================================
# ลบคน พร้อมเส้นความสัมพันธ์ทั้งหมดของคนนั้น
# ==================================================

def delete_user(user_id: str) -> bool:
    rows = run(
        """
        MATCH (u:User {user_id: $user_id})
        DETACH DELETE u          // ลบ node + FRIEND_OF + LIKES ที่ติดอยู่
        RETURN count(*) AS deleted
        """,
        user_id=user_id,
    )
    return bool(rows) and rows[0]["deleted"] > 0