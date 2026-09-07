from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.crew.manager import CrewManager
from app.crew.schemas import CrewCreate, CrewRead, CrewUpdate
from app.database import get_db

router = APIRouter(prefix="/crew", tags=["crew"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CrewRead, status_code=status.HTTP_201_CREATED)
def create_crew(data: CrewCreate, db: DatabaseSession) -> CrewRead:
    return CrewManager(db).create_crew(data)


@router.get("", response_model=list[CrewRead])
def list_crew(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[CrewRead]:
    return CrewManager(db).list_crew(offset=offset, limit=limit)


@router.get("/{crew_id}", response_model=CrewRead)
def get_crew(crew_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> CrewRead:
    return CrewManager(db).get_crew(crew_id)


@router.patch("/{crew_id}", response_model=CrewRead)
def update_crew(
    crew_id: Annotated[int, Path(gt=0)], data: CrewUpdate, db: DatabaseSession
) -> CrewRead:
    return CrewManager(db).update_crew(crew_id, data)


@router.delete("/{crew_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crew(crew_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    CrewManager(db).delete_crew(crew_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
