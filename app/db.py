import psycopg
from dateutil.parser import isoparse
import logging
from dotenv import load_dotenv
import os


load_dotenv()

class DBInterface:
    """Interface for commits API endpoint to communicate with the DB."""
    CONN_DETAILS = os.getenv('CONN_DETAILS')
    
    def __init__(self) -> None:
        self.conn = psycopg.connect(self.CONN_DETAILS)
        
        logging.basicConfig(level=logging.INFO)
        with self.conn.cursor() as cursor:
            try:
                self.create_table(cursor)
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                raise RuntimeError(f"Error initializing agg_commits: {e}")
    
    def create_table(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agg_commits (
                repo TEXT NOT NULL,
                commit_date DATE NOT NULL,
                commits INT NOT NULL,
                authors TEXT[] NOT NULL,
                PRIMARY KEY (repo, commit_date),
                FOREIGN KEY (repo) REFERENCES repositories(repo) ON DELETE CASCADE
            );
        """)
    
    def get_existing_commits(self, owner, repo, since, until):
        repo_full_name = f"{owner}/{repo}"
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT commit_date
                FROM agg_commits
                WHERE repo = %s AND commit_date BETWEEN %s AND %s
                ORDER BY commit_date;
            """, (repo_full_name, since, until))
            existing_commits = [row[0] for row in cursor.fetchall()]
        return existing_commits
    
    def store_aggregated_commits(self, owner, repo, aggregated_commits) -> None:
        """Store fetched commits"""
        repo_full_name = f"{owner}/{repo}"
        with self.conn.cursor() as cursor:
            for data in aggregated_commits:
                date = isoparse(data['date']).strftime('%Y-%m-%d')
                
                cursor.execute("""
                    INSERT INTO agg_commits (repo, commit_date, commits, authors)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (repo, commit_date)
                    DO UPDATE SET commits = EXCLUDED.commits, authors = EXCLUDED.authors;
                """, (repo_full_name, date, data['commits'], data['authors']))

            self.conn.commit()
    
    def get_aggregated_commit_activity(self, owner, repo, since, until) -> list:
        repo_full_name = f"{owner}/{repo}"
        
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT commit_date, commits, authors
                FROM agg_commits
                WHERE repo = %s AND commit_date BETWEEN %s AND %s
                ORDER BY commit_date;
            """, (repo_full_name, since, until))
            return cursor.fetchall()
        
    def get_repo_creation(self, owner, repo):
        repo_full_name = f'{owner}/{repo}'
        
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT date_created 
                FROM repositories
                WHERE repo = %s;
            """, (repo_full_name,))
                        
            result = cursor.fetchone()
            return result[0] if result else None
    
    def close(self):
        self.conn.close()
        
        
        