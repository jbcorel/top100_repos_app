from pydantic import BaseModel


class RepoModel(BaseModel):
    repo: str
    owner: str
    position_cur: int
    position_prev: int
    stars: int
    watchers: int
    forks: str
    open_issues: int
    language: str

class RepoActivity(BaseModel):
    repo: str
    date: str #date
    authors: list[str]


