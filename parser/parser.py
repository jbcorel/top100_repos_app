from time import sleep
import requests
from requests.exceptions import HTTPError
import logging
from dateutil.parser import isoparse
from parser.db import mainDB
from sys import exit
import os


class Top100Getter:
    TOKEN = os.getenv('TOKEN')
    BASE_URL = 'https://api.github.com'
    HEADERS= {'X-GitHub-Api-Version': '2022-11-28',
                    'accept': 'application/vnd.github+json',
                    'User-Agent': 'jbcorel',
                    'Authorization': f"Bearer {TOKEN}"
                }
    
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)
        
    def getTop100Repos(self) -> dict:
        """Gets a list of top100 repos. Due to the way github search api yields info, once this is done,
        each entry needs to be traversed to get the count of watchers, because subscribers_count is not included
        in the keys of each entry. watchers_count, watchers, startgazers_count all refer to the same thing - stargazers"""
        
        logging.info('Trying to get top 100 repos, starting...')
        params = {"q": "stars:>50000", 
                  "sort": "stars", 
                  "order": "desc", 
                  "per_page": 100}
        
        rsp = requests.get(f"{self.BASE_URL}/search/repositories", 
                            params=params,
                            headers=self.HEADERS)
        
        while not rsp.ok:
            ##is okay for now, but then needs to indicate a client about an error
            logging.info('Unable to get top 100 repos, retrying...')
            sleep(5)
            rsp = requests.get(f"{self.BASE_URL}/search/repositories?q=stars:>=50000&order=desc$page=1&per_page=100",
                               headers=self.HEADERS).json()
            
        return rsp.json()['items']
    
    def getRepoDetails(self, owner, repo) -> dict:
        """Get detailed description for each repo in top100"""
        logging.info(f'Fetching details for repo {owner}/{repo}...')

        t = 1
        while True:
            sleep(t)
            try:
                rsp = requests.get(f'{self.BASE_URL}/repos/{owner}/{repo}', headers=self.HEADERS)
                rsp.raise_for_status()
                break
            except HTTPError as e:
                logging.info(f'an HTTP error occurred while fetching details for repo {owner}/{repo}: {e}. Retrying...')
                t = t + 1
            except Exception as e:
                logging.info(f'an error occurred while fetching details for repo {owner}/{repo}: {e}. Retrying...')
                t = t + 1
        rsp = rsp.json()
        repo = rsp['full_name']
        owner = rsp['owner']['login']
        stars = rsp['stargazers_count']
        watchers = rsp['subscribers_count']
        forks = rsp['forks_count']
        open_issues = rsp['open_issues']
        language = rsp['language']
        date_created = isoparse(rsp['created_at']).strftime('%Y-%m-%d')
        
        return {
            'repo': repo,
            'owner': owner,
            'stars': stars,
            'watchers': watchers,
            'forks': forks,
            'open_issues': open_issues,
            'language': language,
            'date_created': date_created
        }
        
    def parser(self, delay=1) -> list:
        """Retrieve top 100 repos, then traverse an object with top 100 repos to get detailed info on each. A delay is meant to avoid 403 for too frequent requests"""
        
        repos = self.getTop100Repos() 
        top100Arr = []
        sleep(delay)
        for position, entry in enumerate(repos, start=1):
            owner, repo = entry['owner']['login'], entry['name']
            
            try:
                repoDetails = self.getRepoDetails(owner, repo)
            except Exception as e:
                logging.info(f'An unknown error occured while fetching details for repo {owner}/{repo}: {e}. Retrying...')
                exit() ##stop the parser if something bad be happening
                    
            repoDetails.update({'position_cur': position})
            top100Arr.append(repoDetails)
            logging.info(f'Successfully fetched details for repo {owner}/{repo}')
            
        return top100Arr 
    

# if __name__ == "__main__":
#     db = mainDB()
#     parser = Top100Getter(mainDB)
#     top100Arr = parser.parser()
#     db.upsert_repositories(top100Arr)
#     db.close()
    
    