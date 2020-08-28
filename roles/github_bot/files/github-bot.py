#!/usr/bin/env python3

import json
import requests
import time


with open('/root/.github-api-token') as f:
    token = f.readlines()[0].strip()

# Check for invitations
url = 'https://api.github.com/user/repository_invitations?access_token=%s' % token
r = requests.get(url)
for invitation in r.json():
    url = 'https://api.github.com/user/repository_invitations/%d?access_token=%s' % (invitation['id'], token)
    r = requests.patch(url)
    print('Accepted invitation to %s' % invitation['repository']['full_name'])

# Check for repositories
repos = []

url = 'https://api.github.com/user/repos?access_token=%s' % token
r = requests.get(url)
for raw_repo in r.json():
    # Skip own repos
    if raw_repo['owner']['login'] in ['ica0002-bot']:
        continue

    repo = {
        'full_name': raw_repo['full_name'],
        'name': raw_repo['name'],
        'owner_key_added': False,
        'owner_login': raw_repo['owner']['login'],
        'owner_url': raw_repo['owner']['html_url'],
        'private': raw_repo['private'],
        'pushed_at': raw_repo['pushed_at'],
        'ready': False,
        'url': raw_repo['html_url'],
    }

    # Check for user SSH keys
    key_url = '%s.keys' % raw_repo['owner']['html_url']
    r = requests.get(key_url)
    if r.text.startswith('ssh-'):
        repo['owner_key_added'] = True

    if repo['private'] and repo['owner_key_added']:
        repo['ready'] = True

    repos.append(repo)

repos = sorted(repos, key=lambda k: k['owner_login'])

# Compose HTML
html = '''
<html>
    <head>
        <meta http-equiv="refresh" content="30">
        <title>Students - ICA0002 2020</title>
        <link rel="stylesheet" type="text/css" href="style.css">
    </head>
    <body>
        <h1><a href="/">ICA0002 2020</a> &raquo; Students</h1>
        <table>
            <tr>
                <th>GitHub user</th>
                <th>Repository</th>
                <th>Private?</th>
                <th>SSH key added?</th>
                <th>Status</th>
            </tr>
'''

now = int(time.time())

for repo in repos:
    html += '<tr>'
    html += '<td><a href="%s">%s</a></td>' % (repo['owner_url'], repo['owner_login'])
    html += '<td><a href="%s">%s</a></td>' % (repo['url'], repo['name'])

    if repo['private']:
        html += '<td class="ok">Yes</td>'
    else:
        html += '<td class="fail">No</td>'

    if repo['owner_key_added']:
        html += '<td class="ok">Yes</td>'
    else:
        html += '<td class="fail">No</td>'

    if repo['ready']:
        html += '<td class="ok">All set up</td>'
    else:
        html += '<td class="fail">In progress...</td>'

    # We'll enable that after week 2 or smth.
    #last_active_time_hours = (now - int(time.mktime(time.strptime(repo['pushed_at'], '%Y-%m-%dT%H:%M:%SZ')))) / 3600
    #if last_active_time_hours < 1:
    #    html += '<td class="ok"><abbr title="%s">less than an hour ago</abbr></td>' % repo['pushed_at']
    #elif last_active_time_hours < 24:
    #    html += '<td class="ok"><abbr title="%s">less than a day ago</abbr></td>' % repo['pushed_at']
    #elif last_active_time_hours < 24 * 7:
    #    html += '<td><abbr title="%s">less than a week ago</abbr></td>' % repo['pushed_at']
    #elif last_active_time_hours < 24 * 14:
    #    html += '<td><abbr title="%s">less than two weeks ago</abbr></td>' % repo['pushed_at']
    #else:
    #    html += '<td class="fail"><abbr title="%s">more that two weeks ago</abbr></td>' % repo['pushed_at']

    html += '</tr>'

html += '''
        </table>
        <div class="footer">Last checked on %s.</div>
    </body>
</html>
''' % time.strftime('%b %d at %H:%M %Z')

with open('/opt/ica0002/pub/students.html', 'w') as f:
    f.write(html)

# Dump list of repo owners
repo_owners = sorted([r['owner_login'] for r in repos])
with open('/opt/ica0002/data/students-with-github-set-up.txt', 'w') as f:
    f.write('\n'.join(repo_owners) + '\n')

# Dump list of GitHub repos
ready_repos = []
for repo in repos:
    if repo['ready']:
        ready_repos.append(repo['full_name'])
with open('/opt/ica0002/data/github-repos.txt', 'w') as f:
    f.write('\n'.join(ready_repos) + '\n')
