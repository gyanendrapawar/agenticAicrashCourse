import json
import time

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# connect to redis (default host and port)
cache = redis.Redis(host="localhost", port=6379, decode_responses=True)

CACHE_TTL = 60  # seconds before a cached item expires

# pretend database
books = {
    1: {"id": 1, "title": "Clean Code", "author": "Robert Martin"},
    2: {"id": 2, "title": "Deep Work", "author": "Cal Newport"},
}


class BookUpdate(BaseModel):
    title: str
    author: str


# pretend the database is slow
def read_from_db(book_id: int):
    time.sleep(2)
    return books.get(book_id)


@app.get("/books/{book_id}")
def get_book(book_id: int):
    key = f"book:{book_id}"

    # 1. look in the cache first
    cached = cache.get(key)
    if cached:
        return {"source": "cache", "data": json.loads(cached)}

    # 2. not in cache, so go to the database
    book = read_from_db(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # 3. save it in the cache for next time
    cache.setex(key, CACHE_TTL, json.dumps(book))
    return {"source": "database", "data": book}


@app.put("/books/{book_id}")
def update_book(book_id: int, new_data: BookUpdate):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")

    books[book_id] = {"id": book_id, "title": new_data.title, "author": new_data.author}

    # the cached copy is old now, so delete it
    cache.delete(f"book:{book_id}")
    return {"message": "Book updated, cache cleared"}