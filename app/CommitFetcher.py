import psycopg
import requests 
import datetime
from datetime import datetime, date, timezone
from time import sleep 
import logging
from collections import defaultdict
import os

class CommitFetcher:
    """API interface to fetch commits from GitHub. Aggregates commits for a given range of date, which is then used to pass to commit DB interface"""
    
    TOKEN = os.getenv('TOKEN')
    BASE_URL = 'https://api.github.com'
    HEADERS = {'X-GitHub-Api-Version': '2022-11-28',
                        'accept': 'application/vnd.github+json',
                        'User-Agent': 'jbcorel',
                        'Authorization': f"Bearer {TOKEN}"
                    }
    
    def fetch_commits(self, owner, repo, since, until) -> list[dict]:
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {"since": since, "until": until, "per_page": 100}
        commits = []

        while url:
            sleep(1)
            response = requests.get(url, headers=self.HEADERS, params=params)
            response.raise_for_status()
            page_commits = response.json()
            commits.extend(page_commits)
            
            links = response.headers.get('Link')
            if links:
                url = None
                for link in links.split(','):
                    if 'rel="next"' in link:
                        url = link[link.find('<') + 1:link.find('>')]
                        break
            else:
                url = None
                
        return commits if commits else until

    def aggregate_commits(self, commits: list) -> list[dict]:
        """Parses a dictionary with detailed info on commits within a specific range,
        then returns an array with date, commits, [authors] as keys."""
        aggregated_data = defaultdict(lambda: {'commits': 0, 'authors': set()}) 
        
        if isinstance(commits, date):
            no_commit_date = datetime.combine(commits, datetime.min.time()).replace(tzinfo=timezone.utc)
            no_commit_date = str(no_commit_date)
            return [{'date': no_commit_date, 'commits': 0, 'authors': []}]
        
        for commit in commits:
            commit_date = commit['commit']['author']['date']
            author = commit['commit']['author']['name']
            aggregated_data[commit_date]['commits'] += 1
            aggregated_data[commit_date]['authors'].add(author)

        return [
            {"date": date, "commits": data['commits'], "authors": list(data['authors'])}
            for date, data in aggregated_data.items()
        ] 
        
    def get_commits(self, owner, repo, since, until):
        logging.info(f'Getting commits for {repo} since {since} until {until}...')
        
        commits = self.fetch_commits(owner, repo, since, until)
        agg_commits = self.aggregate_commits(commits)
        return agg_commits
