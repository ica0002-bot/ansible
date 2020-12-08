#!/usr/bin/env python3

import json
import requests
import time


with open('/root/.github-api-token') as f:
    token = f.readlines()[0].strip()

auto_accept_invites = False

header = { 'Authorization': 'token %s' % token }
# Check for invitations
url = 'https://api.github.com/user/repository_invitations'
r = requests.get(url, headers=header)
for invitation in r.json():
    if auto_accept_invites:
        url = 'https://api.github.com/user/repository_invitations/%d' % invitation['id']
        r = requests.patch(url, headers=header)
        print('Accepted invitation to %s' % invitation['repository']['full_name'])
    else:
        print('Pending invitation to %s. Auto-accept is off' % invitation['repository']['full_name'])

# Check for repositories
repos = []
ready_repo_count = 0
active_repo_count = 0

url = 'https://api.github.com/user/repos?per_page=100'
r = requests.get(url, headers=header)

now = int(time.time())

for raw_repo in r.json():
    # Skip own repos
    if raw_repo['owner']['login'] in ['ica0002-bot']:
        continue

    repo = {
        'active': False,
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

    if repo['private'] and repo['owner_key']:
        repo['ready'] = True
        ready_repo_count += 1

    if repo['ready'] and repo['last_activity_time_days'] < 15:
        repo['active'] = True
        active_repo_count += 1

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
        <a href="/">ICA0002 2020</a> &raquo; <a href="/students.html">Students</a>
        <h1>ICA0002 2020 Students</h1>
        <table>
            <tr>
                <th>GitHub user</th>
                <th>Repository</th>
                <th>Private?</th>
                <th>SSH key</th>
                <th>Last activity</th>
                <th>&nbsp;</th>
            </tr>
'''

for repo in repos:
    comment = '&nbsp;'

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

    comment = '<a href="/results/%s.html">Results</a>' % repo['owner_login']
    last_activity_time_str = time.strftime('%b %e', repo['last_activity_time'])
    if not repo['ready']:
        html += '<td class="fail">---</td>'
        comment += ' | Please complete the repository setup so we could start some VMs for you.'
    elif repo['last_activity_time_days'] < 8:
        html += '<td class="ok">%s</td>' % last_activity_time_str
    elif repo['last_activity_time_days'] < 15:
        html += '<td>%s</td>' % last_activity_time_str
        comment += ' | Recently there were no activity in the repository. VMs may be deleted soon. Please add a few commits to keep the VMs running.'
    else:
        html += '<td class="fail">%s</td>' % last_activity_time_str
        comment += ' | VMs were deleted due to no recent activity in the repository. Please add a few commits, and VMs will be restored soon after.'

    html += '<td class="comment">%s</td>' % comment
    html += '</tr>'

html += '''
            <tr><th colspan="6">Total: %d &nbsp; &middot; &nbsp; Ready: %d &nbsp; &middot; &nbsp; Active: %d</th>
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
''' % (len(repos), ready_repo_count, active_repo_count, time.strftime('%b %d at %H:%M %Z'))

with open('/opt/ica0002/pub/students.html', 'w') as f:
    f.write(html)

# Dump list of GitHub repos and repo owners
with open('/opt/ica0002/data/known-students.txt', 'w') as f:
    f.write('\n'.join([r['owner_login'] for r in repos]) + '\n')

with open('/opt/ica0002/data/active-students.txt', 'w') as f:
    f.write('\n'.join([r['owner_login'] for r in repos if r['active']]) + '\n')

with open('/opt/ica0002/data/known-repos.txt', 'w') as f:
    f.write('\n'.join([r['full_name'] for r in repos]) + '\n')

with open('/opt/ica0002/data/ready-repos.txt', 'w') as f:
    f.write('\n'.join([r['full_name'] for r in repos if r['ready']]) + '\n')

with open('/opt/ica0002/data/active-repos.txt', 'w') as f:
    f.write('\n'.join([r['full_name'] for r in repos if r['active']]) + '\n')
