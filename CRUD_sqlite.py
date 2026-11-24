import sqlite3
from typing import Optional
 
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
 
app = FastAPI()
 
DB_FILE = "todo.db"
 
 
# open a connection to the sqlite file
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row   # lets us read columns by name
    return conn
 
 
# create the table when the app starts
def create_table():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()
 
 
create_table()
 
 
# schema for the data we accept
class Todo(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
 
 
# turn a database row into a normal dictionary
def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "completed": bool(row["completed"]),
    }
 
 
# home page (the UI)
@app.get("/")
def home():
    return FileResponse("static/index.html")
 
 
# CREATE
@app.post("/todos", status_code=201)
def add_todo(todo: Todo):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO todos (title, description, completed) VALUES (?, ?, ?)",
        (todo.title, todo.description, int(todo.completed)),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"message": "Todo added", "id": new_id}
 
 
# READ all  <- open http://127.0.0.1:8000/todos to see the output
@app.get("/todos")
def get_all_todos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM todos").fetchall()
    conn.close()
    return {"total": len(rows), "todos": [row_to_dict(r) for r in rows]}
 
 
# READ one
@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return row_to_dict(row)
 
 
# UPDATE
@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, todo: Todo):
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE todos SET title = ?, description = ?, completed = ? WHERE id = ?",
        (todo.title, todo.description, int(todo.completed), todo_id),
    )
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo updated"}
 
 
# DELETE
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted"}
 