from pydantic import BaseModel
from typing import List, Optional, Annotated, Tuple
from fastapi import Query
from fastapi.exceptions import HTTPException
from datetime import date, datetime, timezone
from app.db import DBInterface


class Repository(BaseModel):
    repo: str
    owner: str
    position_cur: int
    position_prev: Optional[int]
    stars: int
    watchers: int
    forks: int
    open_issues: int
    language: Optional[str] 
    
class RepoActivity(BaseModel):
    date: date
    commits: int
    authors: List[str]
    


queryParam = Annotated[str, Query(pattern=r'^\d{4}-\d{2}-\d{2}$')]

async def query_params(since: queryParam, until: queryParam) -> Tuple[datetime, datetime]:
    if not since or not until:
        raise HTTPException(403, detail="Please provide both 'since' and 'until' parameters")
    try:
        since_date = datetime.strptime(since, '%Y-%m-%d').date()
        until_date = datetime.strptime(until, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=403, detail='Invalid format of since and/or until date(s). Should be in the format of yyyy-mm-dd')
    if since_date > until_date:
        raise HTTPException(status_code=403, detail='Since cannot be bigger than until')
    current_date = datetime.now(tz=timezone.utc).date()
    if until_date > current_date:
        raise HTTPException(status_code=403, detail='Until parameter cannot exceed current date (UTC)')
    
    return since_date, until_date, current_date

def repos_to_pydantic(queryset) -> List[Repository]:
    return [
        Repository(
            repo = row[0],
            owner = row[1],
            position_cur = row[2],
            position_prev = row[3],
            stars = row[4],
            watchers = row[5],
            forks = row[6],
            open_issues = row[7],
            language = row[8]
        )
        for row in queryset
    ]

def activity_to_pydantic (queryset) -> List[RepoActivity]:
    return [
        RepoActivity(
            date = row[0],
            commits = row[1],
            authors = row[2]
        )
        for row in queryset
    ]
    

def get_db ():
    db = DBInterface()
    try: 
        yield db
    finally:
        db.close()