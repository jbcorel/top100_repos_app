from fastapi import FastAPI
from datetime import datetime, timedelta, timezone
from fastapi.exceptions import HTTPException
import logging
from app.commits import DBInterface
from app.CommitFetcher import CommitFetcher
from app.models import RepoModel


app = FastAPI()


@app.get('/api/repos/top100')
async def getTop100():
    return {"hello": "world"}

@app.get('/api/repos/{owner}/{repo}/activity')
async def getRepoActivity(owner: str, repo: str, since: str, until: str):
    if not since or not until:
        return HTTPException(403, detail="Please provide both 'since' and 'until' parameters")
    
    try:
        since_date = datetime.strptime(since, '%Y-%m-%d').date()
        until_date = datetime.strptime(until, '%Y-%m-%d').date()
    except ValueError:
        return HTTPException(status_code=403, detail='Invalid format of since and until date(s). Should be in the format of yyyy-mm-dd')
    
    if since_date > until_date:
        return HTTPException(status_code=403, detail='Since cannot be bigger than until')
    
    current_date = datetime.now(tz=timezone.utc).date()
    if until_date > current_date:
        return HTTPException(status_code=403, detail='Until parameter cannot exceed current date (UTC)')
    
    ##perhaps move outside of endpoint to avoid overly frequent requests to DB (tho will likely be injected as dependency)
    commit_db = DBInterface()
    
    repo_creation_date = commit_db.get_repo_creation(owner, repo)
    #ensure this repo exists at all
    if repo_creation_date:
        if since_date < repo_creation_date or until_date < repo_creation_date:
            return HTTPException(status_code=403, detail=f"Invalid datarange specified: provide a range between {repo_creation_date} and {current_date}.")
    else:
        commit_db.close()
        return HTTPException(status_code=404, detail='Given repository cannot be found in top 100. Possibly, there was a type in your request.')
    
    commit_fetcher = CommitFetcher()

    # Check for existing aggregated data in the database
    existing_dates = commit_db.get_existing_commits(owner, repo, since_date, until_date)

    # Determine missing dates through set operations
    existing_dates = set(existing_dates)
    all_dates = {since_date + timedelta(days=x) for x in range((until_date - since_date).days + 1)}
    missing_dates = all_dates.difference(existing_dates)
    
    logging.info(all_dates)
    logging.info(missing_dates)
    logging.info(existing_dates)
    logging.info(all_dates == missing_dates)

    # Fetch and store missing commits if there any of the dates are not in the db
    if missing_dates:
        if all_dates == missing_dates:
            aggregated_commits = commit_fetcher.get_commits(owner, repo, since_date-timedelta(days=1), until_date)
            commit_db.store_aggregated_commits(owner, repo, aggregated_commits)
        else:
            for date in missing_dates:
                prev_date = date - timedelta(days=1)
                aggregated_commits = commit_fetcher.get_commits(owner, repo, prev_date, date)
                commit_db.store_aggregated_commits(owner, repo, aggregated_commits)

    # Fetch the aggregated commit activity from the database
    activity = commit_db.get_aggregated_commit_activity(owner, repo, since_date, until_date)
    
    commit_db.close()

    return activity

