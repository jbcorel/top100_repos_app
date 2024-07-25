from pydantic import BaseModel
from typing import List, Optional
from datetime import date


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