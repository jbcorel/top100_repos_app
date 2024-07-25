from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import app.models as models
from typing import List, Annotated
from datetime import datetime, timedelta, timezone
from fastapi.exceptions import HTTPException
from app.db import DBInterface
from app.CommitFetcher import CommitFetcher


app = FastAPI()

app.mount("/static", StaticFiles(directory="client/static"), name="static")

@app.get('/')
async def root():
    with open("client/templates/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)
    

@app.get('/api/repos/top100', response_model=List[models.Repository])
async def getTop100():
    db = None
    try:
        db = DBInterface()
        top100_raw = db.get_top100()
        top100 = models.repos_to_pydantic(top100_raw)
        return top100
    except Exception as e:
        return HTTPException(status_code=500, detail=f'Internal server error. Try again later, {e}')
    finally:
        if db:
            db.close()

@app.get('/api/repos/{owner}/{repo}/activity', response_model = List[models.RepoActivity])
async def getRepoActivity(owner: str, 
                          repo: str, 
                          since: Annotated[str, Query(pattern='^\d{4}-\d{2}-\d{2}$')] = ..., 
                          until: Annotated[str, Query(pattern='^\d{4}-\d{2}-\d{2}$')] = ...):
    
    if not since or not until:
        return HTTPException(403, detail="Please provide both 'since' and 'until' parameters")
    
    try:
        since_date = datetime.strptime(since, '%Y-%m-%d').date()
        until_date = datetime.strptime(until, '%Y-%m-%d').date()
    except ValueError:
        return HTTPException(status_code=403, detail='Invalid format of since and/or until date(s). Should be in the format of yyyy-mm-dd')
    
    if since_date > until_date:
        return HTTPException(status_code=403, detail='Since cannot be bigger than until')
    
    current_date = datetime.now(tz=timezone.utc).date()
    if until_date > current_date:
        return HTTPException(status_code=403, detail='Until parameter cannot exceed current date (UTC)')
    
    ##perhaps move outside of endpoint to avoid overly frequent requests to DB (tho will likely be injected as dependency)
    db = DBInterface()
    
    repo_creation_date = db.get_repo_creation(owner, repo)
    #ensure this repo exists at all
    if repo_creation_date:
        if since_date < repo_creation_date or until_date < repo_creation_date:
            return HTTPException(status_code=403, detail=f"Invalid datarange specified: provide a range between {repo_creation_date} and {current_date}.")
    else:
        db.close()
        return HTTPException(status_code=404, detail='Given repository cannot be found in top 100. Possibly, there was a type in your request.')
    
    commit_fetcher = CommitFetcher()

    # Check for existing aggregated data in the database
    existing_dates = db.get_existing_commits(owner, repo, since_date, until_date)

    # Determine missing dates through set operations
    existing_dates = set(existing_dates)
    all_dates = {since_date + timedelta(days=x) for x in range((until_date - since_date).days + 1)}
    missing_dates = all_dates.difference(existing_dates)

    # Fetch and store missing commits if there any of the dates are not in the db
    if missing_dates:
        if all_dates == missing_dates:
            try:
                aggregated_commits = commit_fetcher.get_commits(owner, repo, since_date-timedelta(days=1), until_date)
            except Exception as e:
                db.close()
                return HTTPException(status_code=500, detail="An unknown error occurred on the server. Possibly, Github API is not responding. Try again later")
            db.store_aggregated_commits(owner, repo, aggregated_commits)
        else:
            for date in missing_dates:
                prev_date = date - timedelta(days=1)
                try:
                    aggregated_commits = commit_fetcher.get_commits(owner, repo, prev_date, date)
                except Exception as e:
                    db.close()
                    return HTTPException(status_code=500, detail="An unknown error occurred on the server. Possibly, Github API is not responding. Try again later")
                db.store_aggregated_commits(owner, repo, aggregated_commits)

    # Fetch the aggregated commit activity from the database
    activity_raw = db.get_aggregated_commit_activity(owner, repo, since_date, until_date)
    
    db.close()

    activity = models.activity_to_pydantic(activity_raw)

    return activity

