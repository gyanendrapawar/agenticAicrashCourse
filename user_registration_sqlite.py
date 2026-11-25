import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from hashlib import sha256

app = FastAPI()

# Create table
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")
 
conn.commit()
conn.close()


class UserRegister(BaseModel):
    email: EmailStr
    password: str


@app.post("/register")
def register(user: UserRegister):

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (user.email,)
    )
    #if email exists select * will return a row
    #cursor.fetchone() fetches one line, this will be one line that was returned by select *
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = sha256(
        user.password.encode()
    ).hexdigest()
    
    #insert name email and hased password in database 
    cursor.execute(
        "INSERT INTO users(email,password) VALUES(?,?)",
        (user.email, hashed_password)
    )

    conn.commit()
    conn.close()

    return {"message": "User registered successfully"}