from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from src.api import db
from src.api.models import Note, NoteCreate, NoteUpdate

openapi_tags = [
    {"name": "Health", "description": "Service health and diagnostics."},
    {"name": "Notes", "description": "CRUD operations for notes."},
]

app = FastAPI(
    title="Simple Notes Manager API",
    description="Backend API for a simple notes app. Provides CRUD endpoints backed by SQLite.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Keep CORS compatible with the React frontend container.
# If you want to restrict origins in production, set them here accordingly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    """Initialize SQLite schema on application startup."""
    db.init_db()


@app.get("/", tags=["Health"], summary="Health Check", operation_id="health_check")
def health_check():
    """Basic health endpoint used for service readiness checks."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[Note],
    tags=["Notes"],
    summary="List notes",
    operation_id="list_notes",
)
def list_notes(
    limit: int = Query(default=100, ge=1, le=500, description="Max number of notes to return."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    q: Optional[str] = Query(default=None, description="Optional search query over title/content."),
):
    """List notes ordered by most recently updated, with optional search."""
    notes = db.list_notes(limit=limit, offset=offset, q=q)
    return notes


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Get a note",
    operation_id="get_note",
)
def get_note(note_id: int):
    """Fetch a single note by id."""
    note = db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=Note,
    status_code=status.HTTP_201_CREATED,
    tags=["Notes"],
    summary="Create a note",
    operation_id="create_note",
)
def create_note(payload: NoteCreate):
    """Create a new note."""
    note = db.create_note(title=payload.title, content=payload.content)
    return note


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Update a note",
    operation_id="update_note",
)
def update_note(note_id: int, payload: NoteUpdate):
    """Update an existing note (partial update supported)."""
    updated = db.update_note(note_id=note_id, title=payload.title, content=payload.content)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return updated


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notes"],
    summary="Delete a note",
    operation_id="delete_note",
)
def delete_note(note_id: int):
    """Delete a note by id."""
    deleted = db.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
