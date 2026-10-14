import sqlite3
import re
from collections import defaultdict
from datetime import datetime, timezone

from .config import DB_PATH
from .security import hash_password, verify_password


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = connect()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee','project_head','ceo')),
            is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL, access_level TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
            title TEXT NOT NULL, file_type TEXT NOT NULL, source_type TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL, uploaded_at TEXT NOT NULL, status TEXT NOT NULL,
            version TEXT, access_level TEXT NOT NULL, content TEXT
        );
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL, rationale TEXT,
            alternatives TEXT, status TEXT NOT NULL, proposer_id INTEGER NOT NULL,
            owner_id INTEGER, approver_id INTEGER, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, evidence TEXT
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            project_id INTEGER, message TEXT NOT NULL, notification_type TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT NOT NULL,
            details TEXT, created_at TEXT NOT NULL
        );
        """
    )
    connection.commit()
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed(connection)
    connection.close()


def seed(connection):
    timestamp = now()
    users = [
        ("alice.employee@provenance.local", "Alice Nguyen", "employee"),
        ("morgan.head@provenance.local", "Morgan Lee", "project_head"),
        ("dana.ceo@provenance.local", "Dana Brooks", "ceo"),
        ("sarah.analyst@provenance.local", "Sarah Patel", "employee"),
    ]
    for email, name, role in users:
        connection.execute(
            "INSERT INTO users(email,password_hash,full_name,role,created_at) VALUES(?,?,?,?,?)",
            (email, hash_password("Password123!"), name, role, timestamp),
        )
    connection.commit()
    ids = {row["email"]: row["id"] for row in connection.execute("SELECT id,email FROM users")}
    projects = [
        ("Northwind CRM", "Customer relationship workstream for enterprise accounts.", "active"),
        ("Identity Modernization", "Authentication and authorization service upgrades.", "active"),
        ("Retail Pulse", "Omnichannel analytics and decision support dashboard.", "monitoring"),
    ]
    for project in projects:
        connection.execute("INSERT INTO projects(name,description,status,created_at) VALUES(?,?,?,?)", (*project, timestamp))
    connection.commit()
    project_ids = {row["name"]: row["id"] for row in connection.execute("SELECT id,name FROM projects")}
    memberships = [
        ("Northwind CRM", "alice.employee@provenance.local", "member"),
        ("Northwind CRM", "morgan.head@provenance.local", "manager"),
        ("Northwind CRM", "dana.ceo@provenance.local", "executive"),
        ("Identity Modernization", "alice.employee@provenance.local", "member"),
        ("Identity Modernization", "morgan.head@provenance.local", "manager"),
        ("Identity Modernization", "dana.ceo@provenance.local", "executive"),
        ("Retail Pulse", "sarah.analyst@provenance.local", "member"),
        ("Retail Pulse", "morgan.head@provenance.local", "manager"),
        ("Retail Pulse", "dana.ceo@provenance.local", "executive"),
    ]
    for project, email, access in memberships:
        connection.execute(
            "INSERT INTO project_memberships(project_id,user_id,access_level,created_at) VALUES(?,?,?,?)",
            (project_ids[project], ids[email], access, timestamp),
        )
    decisions = [
        (project_ids["Identity Modernization"], "Standardize on PostgreSQL",
         "Use PostgreSQL as the default data store for the identity platform.",
         "Stronger consistency, security controls, and enterprise support.", "Approved",
         ids["alice.employee@provenance.local"], ids["morgan.head@provenance.local"], ids["dana.ceo@provenance.local"]),
        (project_ids["Northwind CRM"], "Shift to lifecycle-based segmentation",
         "Segment customers by lifecycle stage to improve retention messaging.",
         "The previous model was too static.", "Under Review",
         ids["alice.employee@provenance.local"], ids["alice.employee@provenance.local"], ids["morgan.head@provenance.local"]),
        (project_ids["Retail Pulse"], "Pause new onboarding widgets",
         "Suspend rollout until latency and accessibility review passes.",
         "Current onboarding flow has not met audit expectations.", "Proposed",
         ids["sarah.analyst@provenance.local"], ids["sarah.analyst@provenance.local"], None),
    ]
    for row in decisions:
        connection.execute(
            """INSERT INTO decisions(project_id,title,description,rationale,alternatives,status,
            proposer_id,owner_id,approver_id,created_at,updated_at,evidence)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (*row[:4], "Alternatives documented in source", row[4], *row[5:], timestamp, timestamp, "Seeded development record"),
        )
    connection.commit()


def authenticate(email, password):
    connection = connect()
    row = connection.execute(
        "SELECT * FROM users WHERE email=? AND is_active=1", (email.strip().lower(),)
    ).fetchone()
    connection.close()
    return dict(row) if row and verify_password(password, row["password_hash"]) else None


def register_user(name, email, password, role):
    if not name.strip() or not email.strip() or not password:
        raise ValueError("Name, email, and password are required.")
    connection = connect()
    try:
        cursor = connection.execute(
            "INSERT INTO users(email,password_hash,full_name,role,created_at) VALUES(?,?,?,?,?)",
            (email.strip().lower(), hash_password(password), name.strip(), role, now()),
        )
        user_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO notifications(user_id,message,notification_type,created_at) VALUES(?,?,?,?)",
            (user_id, "Welcome to Provenance.", "welcome", now()),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.close()
        raise ValueError("An account with that email already exists.") from exc
    connection.close()
    return user_id


def log_event(user_id, action, details):
    connection = connect()
    connection.execute(
        "INSERT INTO audit_logs(user_id,action,details,created_at) VALUES(?,?,?,?)",
        (user_id, action, details, now()),
    )
    connection.commit()
    connection.close()


def user_projects(user_id):
    connection = connect()
    role = connection.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
    if not role:
        connection.close()
        return []
    if role["role"] == "ceo":
        rows = connection.execute("SELECT * FROM projects ORDER BY name").fetchall()
    else:
        rows = connection.execute(
            "SELECT p.* FROM projects p JOIN project_memberships m ON m.project_id=p.id WHERE m.user_id=? ORDER BY p.name",
            (user_id,),
        ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def authorized_project_ids(user):
    return [project["id"] for project in user_projects(user["id"])] if user else []


def can_access_project(user_id, project_id):
    return any(project["id"] == project_id for project in user_projects(user_id))


def project_members(project_id):
    connection = connect()
    rows = connection.execute(
        "SELECT u.full_name,u.role,m.access_level FROM users u JOIN project_memberships m ON m.user_id=u.id WHERE m.project_id=?",
        (project_id,),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def project_documents(project_id):
    connection = connect()
    rows = connection.execute(
        "SELECT d.*,u.full_name AS uploader_name FROM documents d JOIN users u ON u.id=d.uploaded_by WHERE d.project_id=? ORDER BY d.uploaded_at DESC",
        (project_id,),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def document(document_id):
    connection = connect()
    row = connection.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    connection.close()
    return dict(row) if row else None


def delete_document_data(document_id):
    connection = connect()
    connection.execute(
        "DELETE FROM decisions WHERE evidence LIKE ?",
        (f"%document:{document_id}%",),
    )
    connection.execute("DELETE FROM document_chunks WHERE document_id=?", (document_id,))
    connection.execute("DELETE FROM documents WHERE id=?", (document_id,))
    connection.commit()
    connection.close()


def user_decisions(user_id):
    connection = connect()
    rows = connection.execute(
        """SELECT d.*,p.name AS project_name,o.full_name AS owner_name
        FROM decisions d JOIN projects p ON p.id=d.project_id
        LEFT JOIN users o ON o.id=d.owner_id
        WHERE d.proposer_id=? OR d.owner_id=? OR d.approver_id=? ORDER BY d.updated_at DESC""",
        (user_id, user_id, user_id),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def project_decisions(project_id):
    connection = connect()
    rows = connection.execute(
        """SELECT d.*,p.name AS project_name,o.full_name AS owner_name
        FROM decisions d JOIN projects p ON p.id=d.project_id
        LEFT JOIN users o ON o.id=d.owner_id WHERE d.project_id=? ORDER BY d.updated_at DESC""",
        (project_id,),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def notifications(user_id):
    connection = connect()
    rows = connection.execute(
        "SELECT n.*,p.name AS project_name FROM notifications n LEFT JOIN projects p ON p.id=n.project_id WHERE n.user_id=? ORDER BY n.created_at DESC",
        (user_id,),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def org_summary():
    connection = connect()
    projects = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    decisions = connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    waiting_approval = connection.execute(
        "SELECT COUNT(*) FROM decisions WHERE status IN ('Proposed','Under Review')"
    ).fetchone()[0]
    missing_owner = connection.execute(
        "SELECT COUNT(*) FROM decisions WHERE owner_id IS NULL"
    ).fetchone()[0]
    missing_approval = connection.execute(
        "SELECT COUNT(*) FROM decisions WHERE status != 'Approved' OR approver_id IS NULL"
    ).fetchone()[0]
    documents = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    complete_documents = connection.execute(
        "SELECT COUNT(*) FROM documents WHERE content IS NOT NULL AND length(trim(content)) > 0"
    ).fetchone()[0]
    knowledge_health = round(
        100 * (
            (complete_documents / documents if documents else 1)
            + (1 - missing_owner / decisions if decisions else 1)
            + (1 - missing_approval / decisions if decisions else 1)
        ) / 3
    )
    result = {
        "projects": projects,
        "decisions": decisions,
        "waiting_approval": waiting_approval,
        "high_priority_risks": waiting_approval,
        "conflicts": missing_approval,
        "knowledge_health": knowledge_health,
        "missing_owner": missing_owner,
        "missing_approval": missing_approval,
        "documents": documents,
    }
    connection.close()
    return result


def executive_report():
    connection = connect()
    decisions = connection.execute(
        """SELECT d.title,p.name AS project_name,d.status,d.owner_id,d.approver_id,
        d.updated_at FROM decisions d JOIN projects p ON p.id=d.project_id
        ORDER BY d.updated_at DESC"""
    ).fetchall()
    timeline = connection.execute(
        """SELECT created_at AS event_time, action AS event, details
        FROM audit_logs ORDER BY created_at DESC LIMIT 20"""
    ).fetchall()
    connection.close()
    return {
        "decisions": [dict(row) for row in decisions],
        "timeline": [dict(row) for row in timeline],
    }


def executive_intelligence(user):
    project_ids = authorized_project_ids(user)
    if not project_ids:
        return {"shared_topics": [], "risks": [], "knowledge_gaps": []}
    placeholders = ",".join("?" for _ in project_ids)
    connection = connect()
    projects = connection.execute(
        f"SELECT id,name FROM projects WHERE id IN ({placeholders})", project_ids
    ).fetchall()
    documents = connection.execute(
        f"SELECT project_id,title,content FROM documents WHERE project_id IN ({placeholders})", project_ids
    ).fetchall()
    decisions = connection.execute(
        f"""SELECT project_id,title,status,owner_id,approver_id
        FROM decisions WHERE project_id IN ({placeholders})""", project_ids
    ).fetchall()
    connection.close()

    topic_projects = defaultdict(set)
    for document in documents:
        terms = set(re.findall(r"[a-z][a-z-]{4,}", f"{document['title']} {document['content'] or ''}".lower()))
        for term in terms:
            topic_projects[term].add(document["project_id"])
    project_names = {row["id"]: row["name"] for row in projects}
    shared_topics = [
        {
            "topic": topic,
            "projects": ", ".join(sorted(project_names[project_id] for project_id in project_ids_for_topic)),
            "project_count": len(project_ids_for_topic),
        }
        for topic, project_ids_for_topic in topic_projects.items()
        if len(project_ids_for_topic) > 1
    ]
    shared_topics.sort(key=lambda item: (-item["project_count"], item["topic"]))

    risks = []
    for decision in decisions:
        if decision["status"] in ("Proposed", "Under Review"):
            risks.append({
                "project": project_names[decision["project_id"]],
                "risk": f"Decision awaiting approval: {decision['title']}",
                "priority": "High" if decision["status"] == "Under Review" else "Medium",
            })
        if decision["owner_id"] is None:
            risks.append({
                "project": project_names[decision["project_id"]],
                "risk": f"Decision has no owner: {decision['title']}",
                "priority": "High",
            })

    knowledge_gaps = []
    for project in projects:
        project_documents = [row for row in documents if row["project_id"] == project["id"]]
        project_decisions = [row for row in decisions if row["project_id"] == project["id"]]
        if not project_documents:
            knowledge_gaps.append({"project": project["name"], "gap": "No source documents indexed"})
        if not project_decisions:
            knowledge_gaps.append({"project": project["name"], "gap": "No decisions recorded"})
        if any(not row["approver_id"] for row in project_decisions):
            knowledge_gaps.append({"project": project["name"], "gap": "One or more decisions lack approval"})
    return {
        "shared_topics": shared_topics[:30],
        "risks": risks,
        "knowledge_gaps": knowledge_gaps,
    }
