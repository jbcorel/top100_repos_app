import psycopg
import requests 
import datetime
import pytz
from datetime import datetime 
from time import sleep 
import logging
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv('.env')

class CommitFetcher:

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
                
        for comm in commits: #RMOVE
            print(comm)
            
        return commits

    def aggregate_commits(self, commits):
        aggregated_data = defaultdict(lambda: {'commits': 0, 'authors': set()})

        for commit in commits:
            commit_date = commit['commit']['author']['date'][:10]  # Extract date part only
            author = commit['commit']['author']['name']
            aggregated_data[commit_date]['commits'] += 1
            aggregated_data[commit_date]['authors'].add(author)

        return [
            {"date": date, "commits": data['commits'], "authors": list(data['authors'])}
            for date, data in aggregated_data.items()
        ]

a = CommitFetcher()
commits = a.fetch_commits('freecodecamp', 'freecodecamp', '2024-06-23', '2024-07-24' )
n = a.aggregate_commits(commits)
print (n)