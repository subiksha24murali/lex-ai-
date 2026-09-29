"""Persistence and workflow operations for citizen-lawyer cases."""
from src.auth.db import get_connection


def create_lawyer_profile(user_id, bar_council_number, practice_areas, languages, bio=""):
    with get_connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO lawyer_profiles "
            "(user_id, bar_council_number, practice_areas, languages, bio) VALUES (?, ?, ?, ?, ?)",
            (user_id, bar_council_number.strip(), practice_areas.strip(), languages.strip(), bio.strip()),
        )


def get_lawyer_profile(user_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM lawyer_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def list_lawyers(practice_area=None, language=None):
    query = """SELECT u.id, u.full_name, u.email, p.bar_council_number,
        p.practice_areas, p.languages, p.bio, p.verification_status
        FROM users u JOIN lawyer_profiles p ON p.user_id = u.id
        WHERE u.role = 'lawyer'"""
    values = []
    if practice_area and practice_area != "Any practice area":
        query += " AND p.practice_areas LIKE ?"
        values.append(f"%{practice_area}%")
    if language and language != "Any language":
        query += " AND p.languages LIKE ?"
        values.append(f"%{language}%")
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(query, values).fetchall()]


def create_consultation_request(citizen_id, summary, details, practice_area, language, lawyer_id=None):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO consultation_requests "
            "(citizen_id, lawyer_id, summary, details, practice_area, language) VALUES (?, ?, ?, ?, ?, ?)",
            (citizen_id, lawyer_id, summary.strip(), details.strip(), practice_area, language),
        )
        return cursor.lastrowid


def list_citizen_requests(citizen_id):
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM consultation_requests WHERE citizen_id = ? ORDER BY created_at DESC",
            (citizen_id,),
        ).fetchall()]


def list_lawyer_requests(lawyer_id):
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT r.*, u.full_name AS citizen_name, u.email AS citizen_email "
            "FROM consultation_requests r JOIN users u ON u.id = r.citizen_id "
            "WHERE r.lawyer_id = ? OR (r.lawyer_id IS NULL AND r.status = 'pending') "
            "ORDER BY r.created_at DESC",
            (lawyer_id,),
        ).fetchall()]


def update_request_status(request_id, lawyer_id, status):
    allowed = {"accepted", "declined", "in_progress", "closed"}
    if status not in allowed:
        raise ValueError("Unsupported consultation status")
    with get_connection() as connection:
        connection.execute(
            "UPDATE consultation_requests SET status = ?, lawyer_id = COALESCE(lawyer_id, ?) "
            "WHERE id = ? AND (lawyer_id = ? OR lawyer_id IS NULL)",
            (status, lawyer_id, request_id, lawyer_id),
        )


def send_message(request_id, sender_id, body):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO case_messages (request_id, sender_id, body) VALUES (?, ?, ?)",
            (request_id, sender_id, body.strip()),
        )
        return cursor.lastrowid


def list_messages(request_id):
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT m.*, u.full_name AS sender_name FROM case_messages m "
            "JOIN users u ON u.id = m.sender_id WHERE m.request_id = ? ORDER BY m.created_at",
            (request_id,),
        ).fetchall()]


def schedule_appointment(request_id, citizen_id, lawyer_id, scheduled_for):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO appointments (request_id, citizen_id, lawyer_id, scheduled_for) VALUES (?, ?, ?, ?)",
            (request_id, citizen_id, lawyer_id, scheduled_for),
        )
        return cursor.lastrowid


def add_case_document(request_id, uploader_id, file_name, mime_type, content):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO case_documents "
            "(request_id, uploader_id, file_name, mime_type, content) VALUES (?, ?, ?, ?, ?)",
            (request_id, uploader_id, file_name, mime_type, content),
        )
        return cursor.lastrowid


def list_case_documents(request_id):
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id, request_id, uploader_id, file_name, mime_type, created_at "
            "FROM case_documents WHERE request_id = ? ORDER BY created_at DESC",
            (request_id,),
        ).fetchall()]


def get_case_document(document_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT file_name, mime_type, content FROM case_documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        return dict(row) if row else None