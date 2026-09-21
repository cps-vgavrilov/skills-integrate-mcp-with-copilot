"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR.parent / "data"
DB_PATH = DATA_DIR / "activities.db"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                activity_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                PRIMARY KEY (activity_id, email),
                FOREIGN KEY (activity_id) REFERENCES activities(id)
            )
            """
        )

        if conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0:
            for name, details in DEFAULT_ACTIVITIES.items():
                cursor = conn.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        name,
                        details["description"],
                        details["schedule"],
                        details["max_participants"],
                    ),
                )
                activity_id = cursor.lastrowid
                for email in details["participants"]:
                    conn.execute(
                        "INSERT OR IGNORE INTO participants (activity_id, email) VALUES (?, ?)",
                        (activity_id, email),
                    )

        conn.commit()


def list_activities() -> dict:
    ensure_database()
    with get_connection() as conn:
        activity_rows = conn.execute(
            "SELECT id, name, description, schedule, max_participants FROM activities ORDER BY name"
        ).fetchall()

        result = {}
        for row in activity_rows:
            participant_rows = conn.execute(
                "SELECT email FROM participants WHERE activity_id = ? ORDER BY email",
                (row["id"],),
            ).fetchall()
            result[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [item["email"] for item in participant_rows],
            }
        return result


def get_activity_by_name(activity_name: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, description, schedule, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if row is None:
            return None

        participants = [
            item["email"]
            for item in conn.execute(
                "SELECT email FROM participants WHERE activity_id = ? ORDER BY email",
                (row["id"],),
            ).fetchall()
        ]
        return {
            "name": row["name"],
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants,
        }


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return list_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    activity = get_activity_by_name(activity_name)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    normalized_email = email.strip()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")

    if normalized_email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up",
        )

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(
            status_code=400,
            detail="Activity is full",
        )

    with get_connection() as conn:
        activity_id = conn.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity_id is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        conn.execute(
            "INSERT INTO participants (activity_id, email) VALUES (?, ?)",
            (activity_id["id"], normalized_email),
        )
        conn.commit()

    return {"message": f"Signed up {normalized_email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    activity = get_activity_by_name(activity_name)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    normalized_email = email.strip()
    if normalized_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity",
        )

    with get_connection() as conn:
        activity_id = conn.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity_id is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        conn.execute(
            "DELETE FROM participants WHERE activity_id = ? AND email = ?",
            (activity_id["id"], normalized_email),
        )
        conn.commit()

    return {"message": f"Unregistered {normalized_email} from {activity_name}"}
