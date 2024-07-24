from fastapi import FastAPI
from datetime import datetime, timedelta
from app.models import RepoModel
from fastapi.exceptions import HTTPException
from db.commits import CommitDB
from app.CommitFetcher import CommitFetcher

app = FastAPI()


app.get('/api/repos/top100')
async def getTop100() -> list[RepoModel]:
    pass

app.get('api/repos/{owner}/{repo}/activity')
async def getRepoActivity(owner: str, repo: str, since: str, until: str):

    if not since or not until:
        return HTTPException(403, detail="Please provide both 'since' and 'until' parameters")

    since_date = datetime.strptime(since, '%Y-%m-%d').date()
    until_date = datetime.strptime(until, '%Y-%m-%d').date()

    commit_db = CommitDB()
    commit_fetcher = CommitFetcher()

    # Check for existing aggregated data in the database
    existing_dates = commit_db.get_existing_commits(f"{owner}/{repo}", since_date, until_date)

    # Determine missing dates
    existing_dates = set(existing_dates)
    all_dates = {since_date + timedelta(days=x) for x in range((until_date - since_date).days + 1)}
    missing_dates = sorted(list(all_dates - existing_dates))

    # Fetch and store missing commits if there are any missing dates
    if missing_dates:
        for date in missing_dates:
            next_date = date + timedelta(days=1)
            commits = commit_fetcher.fetch_commits(owner, repo, date, next_date)
            aggregated_commits = commit_fetcher.aggregate_commits(commits)
            commit_db.store_aggregated_commits(f"{owner}/{repo}", aggregated_commits)

    # Fetch the aggregated commit activity from the database
    activity = commit_db.get_aggregated_commit_activity(f"{owner}/{repo}", since_date, until_date)
    commit_db.close()

    return activity



 
