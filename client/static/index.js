document.getElementById('fetchRepos').addEventListener('click', fetchRepositories);

function fetchRepositories() {
    const repoList = document.getElementById('repoList');
    repoList.innerHTML = ''; 
    fetch('/api/repos/top100')
        .then(response => {
            if (!response.ok) {
                console.log(response)
                throw new Error(`HTTP error! Status: ${response.status}. Text: ${error.statusText}`);
            }
            return response.json();
        })
        .then(data => {

            data.forEach(repo => {
                const repoItem = document.createElement('div');
                repoItem.className = 'repo-item';
                repoItem.setAttribute('data-repo', repo.repo);

                repoItem.innerHTML = `
                    <h3>${repo.repo}</h3>
                    <p>Owner: ${repo.owner}</p>
                    <p>Current position: ${repo.position_cur}</p>
                    <p>Previous position: ${repo.position_prev}</p>
                    <p>Stars: ${repo.stars}</p>
                    <p>Watchers: ${repo.watchers}</p>
                    <p>Forks: ${repo.forks}</p>
                    <p>Open Issues: ${repo.open_issues}</p>
                    <p>Language: ${repo.language || 'N/A'}</p>
                    <button onclick="fetchCommitActivity('${repo.repo}')">View Commit Activity</button>
                `;
                repoList.appendChild(repoItem);
            });
        })
        .catch(error => alert('An error occurred', error.status));
}

function fetchCommitActivity(full_repo_name) {
    
    const since = prompt("Enter the start date (YYYY-MM-DD):");
    const until = prompt("Enter the end date (YYYY-MM-DD):");

    const commitActivity = document.createElement('div');
    commitActivity.className = 'commit-activity';

    const owner = full_repo_name.split('/')[0]
    const repo = full_repo_name.split('/')[1]

    fetch(`/api/repos/${owner}/${repo}/activity?since=${since}&until=${until}`)
        .then(response => {
            if (!response.ok) {
                console.log(response)
                throw new Error(`HTTP error! Status: ${response.status}. Text: ${response.body}`);
            }
            return response.json();
        })
        .then(data => {

            data.forEach(activity => {
                const activityItem = document.createElement('div');
                activityItem.className = 'activity-item';
                activityItem.innerHTML = `
                    <h4>Date: ${activity.date}</h4>
                    <p>Commits: ${activity.commits}</p>
                    <p>Authors: ${activity.authors.join(', ')}</p>
                `;
                commitActivity.appendChild(activityItem);
            });

            const repoItem = document.querySelector(`.repo-item[data-repo='${full_repo_name}']`);
            if (repoItem) {
                repoItem.appendChild(commitActivity);
            }
        })
        .catch(error => {
            console.error('Error fetching commit activity:', error);
            alert(`${error}`)
        });
}