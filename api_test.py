from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from zk import ZK
from datetime import datetime, timedelta
from typing import Optional
import traceback

app = FastAPI()

DEVICE_IP = '192.168.68.104'  # Replace with your ZKTeco device IP
PORT = 4370

def connect_device():
    zk = ZK(DEVICE_IP, port=PORT, timeout=5)
    try:
        conn = zk.connect()
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to device: {e}")

class NewUser(BaseModel):
    user_id: str
    name: str
    privilege: int = 0
    password: str = ""

class UserStatusUpdate(BaseModel):
    user_id: str

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/members")
def get_members():
    try:
        conn = connect_device()
        users = conn.get_users()
        members = []
        for u in users:
            members.append({
                "user_id": str(u.user_id),
                "name": str(u.name),
                "privilege": u.privilege or 0
            })
        conn.disconnect()
        return {"members": members}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching members: {str(e)}")

@app.get("/attendance")
def get_attendance(
    hours: Optional[int] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to")
):
    try:
        conn = connect_device()
        logs = conn.get_attendance()
        users = conn.get_users()
        user_map = {str(u.user_id): u.name for u in users}

        if from_date and to_date:
            start = datetime.strptime(from_date, "%Y-%m-%d")
            end = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            filtered_logs = [
                {
                    "user_id": str(log.user_id),
                    "name": user_map.get(str(log.user_id), "Unknown"),
                    "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "check"
                }
                for log in logs if start <= log.timestamp < end
            ]
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered_logs = [
                {
                    "user_id": str(log.user_id),
                    "name": user_map.get(str(log.user_id), "Unknown"),
                    "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "check"
                }
                for log in logs if log.timestamp >= cutoff
            ]
        else:
            filtered_logs = [
                {
                    "user_id": str(log.user_id),
                    "name": user_map.get(str(log.user_id), "Unknown"),
                    "timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "check"
                }
                for log in logs
            ]

        conn.disconnect()
        return {"attendance": filtered_logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attendance: {str(e)}")

@app.post("/user/create")
def create_user(user: NewUser):
    try:
        conn = connect_device()
        conn.set_user(uid=user.user_id, name=user.name, privilege=user.privilege, password=user.password, enabled=True)
        conn.disconnect()
        return {"message": f"User {user.user_id} created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.delete("/user/delete/{user_id}")
def delete_user(user_id: str):
    try:
        conn = connect_device()
        conn.delete_user(uid=user_id)
        conn.disconnect()
        return {"message": f"User {user_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@app.delete("/user/delete_fingerprint/{user_id}")
def delete_fingerprint(user_id: str):
    try:
        conn = connect_device()
        templates = conn.get_templates()
        deleted = 0
        for t in templates:
            if str(t.user_id) == user_id:
                try:
                    conn.delete_user_template(uid=user_id, fid=t.finger_id)
                    deleted += 1
                except:
                    continue
        conn.disconnect()
        return {"message": f"Deleted {deleted} fingerprints for user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting fingerprints: {str(e)}")

@app.get("/user/fingerprints/{user_id}")
def check_fingerprints(user_id: str):
    try:
        conn = connect_device()
        templates = conn.get_templates()
        conn.disconnect()
        user_templates = [t for t in templates if str(t.user_id) == user_id]
        if not user_templates:
            return {"message": f"No fingerprint templates found for user {user_id}"}
        return {
            "user_id": user_id,
            "total_fingerprints": len(user_templates),
            "finger_indexes": [t.finger_id for t in user_templates]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user/enable")
def enable_user(data: UserStatusUpdate):
    try:
        conn = connect_device()
        user = conn.get_user_by_uid(data.user_id)
        conn.set_user(uid=user.user_id, name=user.name, privilege=user.privilege, password=user.password, enabled=True)
        conn.disconnect()
        return {"message": f"User {data.user_id} enabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enabling user: {str(e)}")

@app.post("/user/disable")
def disable_user(data: UserStatusUpdate):
    try:
        conn = connect_device()
        user = conn.get_user_by_uid(data.user_id)
        conn.set_user(uid=user.user_id, name=user.name, privilege=user.privilege, password=user.password, enabled=False)
        conn.disconnect()
        return {"message": f"User {data.user_id} disabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disabling user: {str(e)}")
