import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional
 
import bcrypt
import jwt
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
 
app = FastAPI()
 
DB_FILE = "users.db"
 
# read the secret from an environment variable, the default is only for learning
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-real-projects")
 
 
def get_connection():
    return sqlite3.connect(DB_FILE)
 
 
def create_table():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
 
 
create_table()
 
 
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
 
 
class UserLogin(BaseModel):
    email: EmailStr
    password: str
 
 
@app.post("/register", status_code=201)
def register(user: UserRegister):
    # bcrypt adds a random salt and is slow on purpose, unlike plain sha256
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
 
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (user.email, hashed),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # the UNIQUE rule on email caught a duplicate
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        conn.close()
 
    return {"message": "User registered successfully"}
 
 
@app.post("/login")
def login(user: UserLogin):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, email, password FROM users WHERE email = ?",
        (user.email,),
    ).fetchone()
    conn.close()
 
    # same error for wrong email and wrong password
    if row is None or not bcrypt.checkpw(user.password.encode(), row[2].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
 
    token = jwt.encode(
        {
            "user_id": row[0],
            "email": row[1],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
 
    return {"access_token": token, "token_type": "bearer"}
 
 
# token comes in the Authorization header: "Bearer <token>"
@app.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
 
    token = authorization.removeprefix("Bearer ")
 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
 
    return {"user_id": payload["user_id"], "email": payload["email"]}
 