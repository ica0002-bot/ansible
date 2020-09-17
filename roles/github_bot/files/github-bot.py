#!/usr/bin/env python3

import json
import requests
import time


with open('/root/.github-api-token') as f:
    token = f.readlines()[0].strip()

header = { 'Authorization': 'token %s' % token }
# Check for invitations
url = 'https://api.github.com/user/repository_invitations'
r = requests.get(url, headers=header)
for invitation in r.json():
    url = 'https://api.github.com/user/repository_invitations/%d' % invitation['id']
    r = requests.patch(url, headers=header)
    print('Accepted invitation to %s' % invitation['repository']['full_name'])

# Check for repositories
repos = []

url = 'https://api.github.com/user/repos?per_page=100'
r = requests.get(url, headers=header)

now = int(time.time())

for raw_repo in r.json():
    # Skip own repos
    if raw_repo['owner']['login'] in ['ica0002-bot']:
        continue

    repo = {
        'full_name': raw_repo['full_name'],
        'last_activity_time': None,
        'last_activity_time_days': None,
        'name': raw_repo['name'],
        'owner_key': None,
        'owner_login': raw_repo['owner']['login'],
        'owner_url': raw_repo['owner']['html_url'],
        'private': raw_repo['private'],
        'pushed_at': raw_repo['pushed_at'],
        'ready': False,
        'url': raw_repo['html_url'],
    }

    # Check for user SSH keys
    key = requests.get('%s.keys' % raw_repo['owner']['html_url']).text.strip()
    if key.startswith('ssh-'):
        repo['owner_key'] = key

    repo['last_activity_time'] = time.strptime(repo['pushed_at'], '%Y-%m-%dT%H:%M:%SZ')
    repo['last_activity_time_days'] = (now - int(time.mktime(repo['last_activity_time']))) / 86400

    if repo['private'] and repo['owner_key'] and repo['last_activity_time_days'] < 15:
        repo['ready'] = True

    repos.append(repo)

repos = sorted(repos, key=lambda k: k['owner_login'])

ready_repo_owners = []
ready_repos = []
for repo in repos:
    if repo['ready']:
        ready_repo_owners.append(repo['owner_login'])
        ready_repos.append(repo['full_name'])

# Compose HTML
html = '''
<html>
    <head>
        <meta http-equiv="refresh" content="30">
        <title>Students - ICA0002 2020</title>
        <link rel="stylesheet" type="text/css" href="style.css">
    </head>
    <body>
        <a href="/">ICA0002 2020</a> &raquo; <a href="/students.html">Students</a>
        <h1>ICA0002 2020 Students</h1>
        <table>
            <tr>
                <th>GitHub user</th>
                <th>Repository</th>
                <th>Private?</th>
                <th>SSH key</th>
                <th>Last activity</th>
            </tr>
'''

for repo in repos:
    html += '<tr>'
    html += '<td><a href="%s">%s</a></td>' % (repo['owner_url'], repo['owner_login'])
    html += '<td><a href="%s">%s</a></td>' % (repo['url'], repo['name'])

    if repo['private']:
        html += '<td class="ok">Yes</td>'
    else:
        html += '<td class="fail">No</td>'

    if repo['owner_key']:
        html += '<td class="ok"><a href="%s.keys"><pre>...%s</pre></a></td>' % (repo['owner_url'], repo['owner_key'].split(' ')[-1][-8:])
    else:
        html += '<td class="fail">Not added</td>'
    last_activity_time_str = time.strftime('%b %e', repo['last_activity_time'])
    if not (repo['private'] and repo['owner_key']):
        html += '<td class="fail">---</td>'
    elif repo['last_activity_time_days'] < 8:
        html += '<td class="ok">%s</td>' % last_activity_time_str
    elif repo['last_activity_time_days'] < 15:
        html += '<td>%s</td>' % last_activity_time_str
    else:
        html += '<td class="fail">%s</td>' % last_activity_time_str

    html += '</tr>'

html += '''
            <tr><th colspan="5">Total: %d &nbsp; &middot; &nbsp; Repositories set up: %d</th>
            </tr>
        </table>
        <div class="footer">
            Updated every 15 minutes. Last checked on %s.
            <br><br>
            Cannot find yourself in this list?
            Make sure your GitHub repository is
            <a href="https://github.com/romankuchin/ica0002-2020/blob/master/01-intro/lab.md">set up correctly</a>.
            <br><br>
            If you believe that something is still wrong please
            <a href="https://github.com/romankuchin/ica0002-2020#teacher-contacts">contact us</a>.
        </div>
    </body>
</html>
''' % (len(repos), len(ready_repos), time.strftime('%b %d at %H:%M %Z'))

with open('/opt/ica0002/pub/students.html', 'w') as f:
    f.write(html)

# Dump list of GitHub repos and repo owners
with open('/opt/ica0002/data/students-with-github-set-up.txt', 'w') as f:
    f.write('\n'.join(ready_repo_owners) + '\n')

with open('/opt/ica0002/data/github-repos.txt', 'w') as f:
    f.write('\n'.join(ready_repos) + '\n')
