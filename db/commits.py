import psycopg
import requests 
import datetime
import pytz
from datetime import datetime 
import logging
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv('../.env')

class CommitDB:
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
                repo VARCHAR(255) NOT NULL,
                commit_date DATE NOT NULL,
                commits INT NOT NULL,
                authors TEXT[] NOT NULL,
                PRIMARY KEY (repo, commit_date)
            );
        """)
    
    def get_existing_commits(self, repo, since, until):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT commit_date
                FROM agg_commits
                WHERE repo = %s AND commit_date BETWEEN %s AND %s
                ORDER BY commit_date;
            """, (repo, since, until))
            existing_commits = [row[0] for row in cursor.fetchall()]
        return existing_commits
    
    def store_aggregated_commits(self, repo, aggregated_commits) -> None:
        with self.conn.cursor() as cursor:
            for data in aggregated_commits:
                cursor.execute("""
                    INSERT INTO agg_commits (repo, commit_date, commits, authors)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (repo, commit_date)
                    DO UPDATE SET commits = EXCLUDED.commits, authors = EXCLUDED.authors;
                """, (repo, data['date'], data['commits'], data['authors']))

            self.conn.commit()
    
    def get_aggregated_commit_activity(self, cursor, repo, since, until) -> list:
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT commit_date, commits, authors
                FROM agg_commits
                WHERE repo = %s AND commit_date BETWEEN %s AND %s
                ORDER BY commit_date;
            """, (repo, since, until))
            return cursor.fetchall()
    
    def close(self):
        self.conn.close()
        