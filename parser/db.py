import psycopg
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
import os

load_dotenv()


class mainDB:
    """Interface for the parser to interact with the database. CONN_DETAILS represents psql connection settings in the format of "dbname= host= user= password=" """
    CONN_DETAILS = os.getenv('CONN_DETAILS')
    
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)
        
        with psycopg.connect(self.CONN_DETAILS) as conn:
            with conn.cursor() as cursor:
                try:
                    self.create_repositories(cursor)
                    self.create_repository_history(cursor)

                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise RuntimeError(e)

    
    def create_repositories(self, cursor):
        try:
            cursor.execute("""
                        CREATE TABLE IF NOT EXISTS repositories (
                            repo TEXT PRIMARY KEY,
                            owner TEXT NOT NULL,
                            position_cur INT NOT NULL,
                            position_prev INT,
                            stars INT NOT NULL,
                            watchers INT NOT NULL,
                            forks INT NOT NULL,
                            open_issues INT NOT NULL, 
                            language TEXT,
                            date_created DATE NOT NULL
                        );
                    """)
        except Exception as e:
            raise RuntimeError(f"Exception occurred when initilizing repositories {e}")

    
    def create_repository_history(self, cursor):
        try:
            cursor.execute("""
                        CREATE TABLE IF NOT EXISTS repository_history (
                            repo TEXT NOT NULL,
                            position INT NOT NULL,
                            fetch_date TIMESTAMPTZ NOT NULL,
                            PRIMARY KEY (repo, fetch_date),
                            FOREIGN KEY (repo) REFERENCES repositories(repo)
                        );
                    """)
        except Exception as e:
            raise RuntimeError(f"Exception occurred when initilizing repository_history: {e}")
    
    def get_previous_positions(self, cursor) -> dict:
        try:
            cursor.execute("""
                SELECT repo, position
                FROM (
                    SELECT repo, position, ROW_NUMBER() OVER (PARTITION BY repo ORDER BY fetch_date DESC) as rn
                    FROM repository_history
                ) as subquery
                WHERE rn=2;
            """)
            previous_positions = cursor.fetchall()
            return {row[0]: row[1] for row in previous_positions}
        except Exception as e:
            raise RuntimeError('Unable to get previous positions. Error: %s', e)

    
    def upsert_repositories(self, repositories: list[dict]) -> None:
        """Upserts main table and history tables with new values. For history table, stores fetch_date in UTC"""
        with psycopg.connect(self.CONN_DETAILS) as conn:
            with conn.cursor() as cursor:
                try:
                    previous_positions = self.get_previous_positions(cursor)
                
                    date_fetched = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z%z") #store in UTC time
                    
                    for repo in repositories:
                        previous_position = previous_positions.get(repo['repo'], None) 
                        try:
                            cursor.execute("""
                                INSERT INTO repositories (repo, owner, position_cur, position_prev, stars, watchers, forks, open_issues, language, date_created)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (repo)
                                DO UPDATE SET owner = EXCLUDED.owner,
                                            position_cur = EXCLUDED.position_cur,
                                            position_prev = EXCLUDED.position_prev,
                                            stars = EXCLUDED.stars,
                                            watchers = EXCLUDED.watchers,
                                            forks = EXCLUDED.forks,
                                            open_issues = EXCLUDED.open_issues,
                                            language = EXCLUDED.language,
                                            date_created = EXCLUDED.date_created;
                            """, (
                                repo['repo'],
                                repo['owner'],
                                repo['position_cur'],
                                previous_position,
                                repo['stars'],
                                repo['watchers'],
                                repo['forks'],
                                repo['open_issues'],
                                repo['language'],
                                repo['date_created']
                            ))
                        except Exception as e:
                            raise RuntimeError(f"Unable to insert into repositories. Error: {e}")
                        
                        try:
                            cursor.execute("""
                                INSERT INTO repository_history (repo, fetch_date, position)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (repo, fetch_date)
                                DO NOTHING;
                            """, (
                                repo['repo'], 
                                date_fetched, 
                                repo['position_cur']
                            ))
                        except Exception as e:
                            raise RuntimeError(f"Unable to insert into repository_history. Error: {e}")
                        
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logging.info(e)
            
    
