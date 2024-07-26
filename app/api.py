from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import app.models as models
from typing import List, Annotated, Tuple
from datetime import datetime, timedelta, timezone
from fastapi.exceptions import HTTPException
from app.db import DBInterface
from app.CommitFetcher import CommitFetcher
import logging 


app = FastAPI()

app.mount("/static", StaticFiles(directory="client/static"), name="static")

@app.get('/')
async def root():
    with open("client/templates/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get('/api/repos/top100', response_model=List[models.Repository])
async def getTop100(db: DBInterface = Depends(models.get_db)):
    top100_raw = db.get_top100()
    top100 = models.repos_to_pydantic(top100_raw)
    return top100

@app.get('/api/repos/{owner}/{repo}/activity', response_model = List[models.RepoActivity])
async def getRepoActivity(owner: str, 
                          repo: str, 
                          date_range: Tuple[datetime, datetime] = Depends(models.query_params),
                          db: DBInterface = Depends(models.get_db)):
    
    since_date, until_date, current_date = date_range   
    
    repo_creation_date = db.get_repo_creation(owner, repo)

    if repo_creation_date:
        if since_date < repo_creation_date or until_date < repo_creation_date:
            raise HTTPException(status_code=403, detail=f"Invalid datarange specified: provide a range between {repo_creation_date} and {current_date}.")
    else:
        raise HTTPException(status_code=404, detail='Given repository cannot be found in top 100. Possibly, there was a type in your request.')
    
    commit_fetcher = CommitFetcher()

    existing_dates = db.get_existing_commits(owner, repo, since_date, until_date)

    existing_dates = set(existing_dates)
    all_dates = {since_date + timedelta(days=x) for x in range((until_date - since_date).days + 1)}
    missing_dates = all_dates.difference(existing_dates)

    if missing_dates:
        if all_dates == missing_dates:
            try:
                aggregated_commits = commit_fetcher.get_commits(owner, repo, since_date-timedelta(days=1), until_date)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"An unknown error occurred on the server. Possibly, Github API is not responding, token might be expired. Try again later. {e} ")
            db.store_aggregated_commits(owner, repo, aggregated_commits)
        else:
            for date in missing_dates:
                prev_date = date - timedelta(days=1)
                try:
                    aggregated_commits = commit_fetcher.get_commits(owner, repo, prev_date, date)
                except Exception as e:
                    logging.error(e)
                    raise HTTPException(status_code=500, detail=f"An unknown error occurred on the server. Github API is not responding, token might be expired. Try again later {e}")
                db.store_aggregated_commits(owner, repo, aggregated_commits)

    # Fetch the aggregated commit activity from the database
    activity_raw = db.get_aggregated_commit_activity(owner, repo, since_date, until_date)
    
    activity = models.activity_to_pydantic(activity_raw)

    return activity