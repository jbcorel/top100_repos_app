Парсер топ 100 репозиториев с Github по количеству звезд. Парсер работает каждый час по триггеру в облачной функции в Яндексе. База данных Postgres тоже хостится в облаке Яндекс.

Схема Postgres:
1. CREATE TABLE IF NOT EXISTS repositories (
    repo TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    position_cur INT NOT NULL,
    position_prev INT,
    stars INT NOT NULL,
    watchers INT NOT NULL,
    forks INT NOT NULL,
    open_issues INT NOT NULL, 
    language TEXT,
    date_created DATE NOT NULL); -> Основная таблица. Date_created добавлена для валидации минимального значения параметров запроса since и until

2. CREATE TABLE IF NOT EXISTS repository_history (
    repo TEXT NOT NULL,
    position INT NOT NULL,
    fetch_date TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (repo, fetch_date),
    FOREIGN KEY (repo) REFERENCES repositories(repo)); -> Историческая таблица значения

3. CREATE TABLE IF NOT EXISTS agg_commits (
    repo TEXT NOT NULL,
    commit_date DATE NOT NULL,
    commits INT NOT NULL,
    authors TEXT[] NOT NULL,
    PRIMARY KEY (repo, commit_date),
    FOREIGN KEY (repo) REFERENCES repositories(repo) ON DELETE CASCADE); -> таблица с агрегированной информацией о коммитах.

Принцип работы API:

1. @app.get('/api/repos/top100', response_model=List[models.Repository])
Подключается к облаку с postgres и достает список репозиториев, сортированный по позиции в топе.

2. @app.get('/api/repos/{owner}/{repo}/activity', response_model = List[models.RepoActivity])
 Эндпоинт возвращает количество коммитов и список авторов коммитов в данном репозитории за указанный период. Эндпоинт устанавливает соединение с базой данных посредством интерфеса в db.py, проверяет наличие в базе данных коммитов за указанный период, и, если они отстутсвуют, достает и агрегирует коммиты с Github в базу данных. Затем, из базы данных вытаскиваются эти коммиты. Если коммиты отсутствуют частично (например, нам нужны коммиты с 20 по 31 марта, в дб уже есть коммиты с 25 по 30 марта), то отсутствующие даты вычисляются по формуле и достаются из Github по вышеуказанной схеме. Это сделано для того, чтобы доставать коммиты по необходимости, а не складывать в базу данных все коммиты за все даты с момента создания каждого репозитория.

  P.S. Возвращаются только даты, на которые есть коммиты в промежутке времени. Если в указанном промежутке вообще не было коммитов, то возвращается все даты с пустыми полями. Даты вводить в формате гггг-мм-дд. Нужно нажать на view commit activity и ждать ответа :)

 Запуск:

1. git clone <this repo>
2. Нужно сгенерировать и вставить свой github personal access token в аттрибут TOKEN класса CommitFetcher в CommitFetcher.py. Сделать это можно в настройках профиля - developer settings (в самом низу в панели слева) - Personal access tokens - classic. Никаких разрешений ставить не нужно, просто создать с дефолтными настройками.
3. Настроить соединение с базой данных в Dockerfile или любым другим способом - главное чтобы в переменной среды были параметры подключения, и остальные зависимости вроде сертификатов и тп.
3. docker compose up --build
4. localhost:8000

