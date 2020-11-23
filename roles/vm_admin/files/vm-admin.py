#!/usr/bin/env python3

import json
import requests
import sys
import time


with open('/root/.waldur-api-token') as f:
    token = f.readlines()[0].strip()

headers = {
    'Authorization': 'token %s' % token,
    'Content-Type': 'application/json',
}
base_url = 'https://api.etais.ee/api'
project_id = '22d7e03a0d654f98bd45cafd592ce8a2'
vm1_public_ip = '193.40.156.86'


def format_student(student, active):
    return 'Student %s%s' % (student, '' if active else ' (INACTIVE)')


def get_active_students():
    students = []

    print('Retrieving student info...')
    with open('/opt/ica0002/data/active-students.txt') as f:
        raw_students = f.readlines()
    for raw_student in raw_students:
        students.append(raw_student.strip())

    return students


def get_ready_vm_ips():
    vms = []

    print('Retrieving SSH key info...')
    try:
        with open('/opt/ica0002/data/ready-vms.txt') as f:
            raw_vm_list = f.readlines()
        for vm in raw_vm_list:
            vms.append(vm.strip().split(':')[0])
    except FileNotFoundError:
        pass

    return vms


def get_student_vms(student_query):
    student_vms = {}

    active_students = get_active_students()
    ready_vm_ips = get_ready_vm_ips()
    waldur_vms = get_waldur_vms()
    q = set(student_query.split(','))

    # Add queried students; these may be inactive and do not have any VMs
    # but still should appear in the list
    for student in q:
        if student in {'all', 'active', 'inactive'}:
            continue

        student_vms[student] = {
            'active': False,
            'vms': [],
        }

    # Add active students matching the query that may have some (or no) VMs
    for student in active_students:
        if not q & {'all', 'active', student}:
            continue

        student_vms[student] = {
            'active': True,
            'vms': [],
        }

    # Group existing VMs by student
    for vm in waldur_vms:
        student = vm['description']

        if q & {'active'}:
            if student not in active_students:
                continue
        elif q & {'inactive'}:
            if student in active_students:
                continue
        elif not q & {'all', student}:
            continue

        if student not in student_vms:
            student_vms[student] = {
                'active': False,
                'vms': [],
            }

        if vm['ip'] not in ready_vm_ips:
            vm['public_ssh'] = 'student_key_not_added_yet'

        student_vms[student]['vms'].append(vm)

    return student_vms


def get_waldur_vms():
    vms = []

    print('Retrieving list of VMs from Waldur...')
    r = requests.get('%s/openstacktenant-instances/?page_size=200&project=%s' % (base_url, project_id), headers=headers)
    raw_vm_list = r.json()
    if not isinstance(raw_vm_list, list):
        print('ERROR: Could not get VM list from Waldur. Got this instead:')
        print(raw_vm_list)
        sys.exit(1)

    for vm in raw_vm_list:
        # Skip VMs with empty description
        if 'description' not in vm or not vm['description']:
            continue

        # Skip VMs that do not have an IP address
        if not 'internal_ips' in vm or not vm['internal_ips'] or not vm['internal_ips'][0]:
            continue

        ip = vm['internal_ips'][0]
        vm_id = ip.split('.')[-1]

        vms.append({
            'allowed_addresses': [ i['ip_address'] for i in vm['internal_ips_set'][0]['allowed_address_pairs']],
            'description': vm['description'],
            'ip': ip,
            'name': vm['name'],
            'public_ha_url': 'http://%s:%s88' % (vm1_public_ip, vm_id),
            'public_ssh': 'ubuntu@%s:%s22' % (vm1_public_ip, vm_id),
            'public_url': 'http://%s:%s80' % (vm1_public_ip, vm_id),
            'uuid': vm['uuid'],
        })

    return vms


def print_vms(student_query):
    student_vms = get_student_vms(student_query)
    for student in sorted(student_vms.keys()):
        heading = '\n%s VMs:' % format_student(student, student_vms[student]['active'])
        if not student_vms[student]['vms']:
            print('%s none' % heading)
            continue

        print(heading)
        for vm in student_vms[student]['vms']:
            print('  - %s  %s  %s  %s' % (vm['name'], vm['ip'], vm['public_ssh'], vm['public_url']))


def interpret_status_code(code):
    if code in [200, 201, 202]:
        return '\033[92m[OK]\033[0m'

    if code == 400:
        return '\033[91m[FAIL]\033[0m'

    return code


def create_vm(student, id):
    print('Creating VM %s for %s...' % (id, student))

    payload = {
        'offering': 'https://api.etais.ee/api/marketplace-offerings/b8a3f21d92d9411a89315ab727340471/',
        'project': 'https://api.etais.ee/api/projects/%s/' % project_id,
        'attributes': {
            'name': '%s-%s' % (student, id),
            'description': student,
            'image': 'https://api.etais.ee/api/openstacktenant-images/7054bc7140894afc91af6b84c13a3798/',
            'flavor': 'https://api.etais.ee/api/openstacktenant-flavors/5a8615aa7814412ebc210cb9fb7de26d/',
            'ssh_public_key': 'https://api.etais.ee/api/keys/6ecc7a9f69514c49b076d68245ac66b5/',
            'security_groups': [{
                'url': 'https://api.etais.ee/api/openstacktenant-security-groups/70bdb790eb854be6b596bfdf4a4a572d/',
            }],
            'internal_ips_set': [{
                'subnet': 'https://api.etais.ee/api/openstacktenant-subnets/324153f31fa0485e9aa58d0b5c3b3e2f/',
            }],
            'floating_ips': [],
            'system_volume_size': 10240,
            'system_volume_type': 'https://api.etais.ee/api/openstacktenant-volume-types/c76e8ea53bea4b9a9d626c8590ef5515/',
            'data_volume_type': 'https://api.etais.ee/api/openstacktenant-volume-types/c76e8ea53bea4b9a9d626c8590ef5515/',
        }
    }
    r = requests.post('%s/marketplace-cart-items/' % base_url, headers=headers, data=json.dumps(payload))
    print('Request to create VM. Response: %s' % interpret_status_code(r.status_code))

    payload = {
        'project': 'https://api.etais.ee/api/projects/%s/' % project_id,
    }
    r = requests.post('%s/marketplace-cart-items/submit/' % base_url, headers=headers, data=json.dumps(payload))
    print('Submit request. Response: %s' % interpret_status_code(r.status_code))


def delete_vm(vm_id):
    r = requests.delete('%s/openstacktenant-instances/%s/force_destroy/?delete_volumes=true&release_floating_ips=true' % (base_url, vm_id), headers=headers)
    print('Request to delete VM. Response: %s' % interpret_status_code(r.status_code))


def adjust_vm_count(student_query, vm_count):
    if not 0 <= vm_count <= 3:
        print('ERROR: allowed VM counts are 0, 1, 2 and 3.')
        sys.exit(1)

    student_vms = get_student_vms(student_query)
    for student in sorted(student_vms.keys()):
        actual_vm_count = len(student_vms[student]['vms'])
        diff = abs(actual_vm_count - vm_count)

        print('%s has %d VMs, desired: %d' % (format_student(student, student_vms[student]['active']), actual_vm_count, vm_count))
        if actual_vm_count > vm_count:
            for i in range(int(vm_count), actual_vm_count):
                print('Deleting VM %s...' % student_vms[student]['vms'][i]['name'])
                delete_vm(student_vms[student]['vms'][i]['uuid'])
        elif actual_vm_count < vm_count:
            for i in range(actual_vm_count, int(vm_count)):
                create_vm(student, i + 1)
        print('---')
        time.sleep(2)

    print('All good.')


def print_help():
    print('''Usage: %s <options>

      Options:
        dump         - generate HTML page
        <query>      - print list of VMs for students matching the query
        <query> <n>  - adjust number of VMs: create/delete VMs to match <n>

      Query:
        active                 - match active students
        all                    - match all students
        inactive               - match inactive students
        <student_name>[,<...>] - match these student names (each name exactly, no regexps)

      List of active students can be found in /opt/ica0002/data/active-students.txt.''' % sys.argv[0])


def write_data():
    html = '''
    <html>
        <head>
            <meta http-equiv="refresh" content="30">
            <title>VMs - ICA0002 2020</title>
            <link rel="stylesheet" type="text/css" href="style.css">
        </head>
        <body>
            <a href="/">ICA0002 2020</a> &raquo; <a href="/vms.html">Virtual Machines</a>
            <h1>ICA0002 2020</a> Virtual Machines</h1>
            <table>
                <tr>
                    <th>GitHub user</th>
                    <th>VM names</th>
                    <th>VM IPs</th>
                    <th>Public SSH</th>
                    <th>Public URLs</th>
                    <th>Public HA URLs</th>
                </tr>
    '''

    total_vm_count = 0
    ready_vm_count = 0

    student_vms = get_student_vms('all')
    for student in sorted(student_vms.keys()):
        vm_ips = []
        vm_names = []
        vm_ssh_logins = []
        vm_urls = []
        vm_ha_urls = []

        for vm in student_vms[student]['vms']:
            vm_ips.append(vm['ip'])
            vm_names.append(vm['name'])
            vm_urls.append('<a href="%s">%s</a>' % (vm['public_url'], vm['public_url']))
            vm_ha_urls.append('<a href="%s">%s</a>' % (vm['public_ha_url'], vm['public_ha_url']))

            if vm['public_ssh'] == 'student_key_not_added_yet':
                vm_ssh_logins.append('Still creating...')
            else:
                vm_ssh_logins.append(vm['public_ssh'].replace(':', ' port '))
                ready_vm_count += 1

            total_vm_count += 1

        html += '<tr>'
        html += '<td><a href="https://github.com/%s">%s</a></td>' % (student, student)
        html += '<td>%s</td>' % ('<br>'.join(vm_names or ['---']))
        html += '<td>%s</td>' % ('<br>'.join(vm_ips or ['---']))
        html += '<td>%s</td>' % ('<br>'.join(vm_ssh_logins or ['---']))
        html += '<td>%s</td>' % ('<br>'.join(vm_urls or ['---']))
        html += '<td>%s</td>' % ('<br>'.join(vm_ha_urls or ['---']))
        html += '</tr>'

    html += '''
                <tr><th colspan="6">Total: %d &nbsp; &middot; &nbsp; Ready: %d</th></tr>
            </table>
            <div class="footer">
                Updated every 15 minutes. Last checked on %s.
                <br><br>
                Missing VMs are ususally added within 1..2 hours after your GitHub repository is set up.
                <br><br>
                Cannot find yourself in this list?
                Make sure your GitHub repository is <a href="/students.html">set up correctly</a>.
                <br><br>
                If you believe that something is still wrong please
                <a href="https://github.com/romankuchin/ica0002-2020#teacher-contacts">contact us</a>.
            </div>
        </body>
    </html>
    ''' % (total_vm_count, ready_vm_count, time.strftime('%b %d at %H:%M %Z'))

    with open('/opt/ica0002/pub/vms.html', 'w') as f:
        f.write(html)

def get_vip(vm_ip):
    return '192.168.100.%s' % vm_ip.split('.')[-1]

def allow_additional_ips():
    student_vms = get_student_vms('all')
    for student in sorted(student_vms.keys()):
        expected_allowed_addresses = []
        for vm in student_vms[student]['vms']:
            expected_allowed_addresses.append(get_vip(vm['ip']))
        for vm in student_vms[student]['vms']:
            if sorted(expected_allowed_addresses) != sorted(vm['allowed_addresses']):
                payload = {
                    'subnet': 'https://api.etais.ee/api/openstacktenant-subnets/324153f31fa0485e9aa58d0b5c3b3e2f/',
                    'allowed_address_pairs': [
                        {'ip_address': ip } for ip in expected_allowed_addresses
                    ]
                }
                request_url = '%s/openstacktenant-instances/%s/update_allowed_address_pairs/' % (base_url, vm['uuid'])
                r = requests.post(request_url, headers=headers, data=json.dumps(payload))
                print('Request to update allowed IPs. Response: %s' % interpret_status_code(r.status_code))


if len(sys.argv) < 2:
    print_help()
    sys.exit(1)
elif sys.argv[1] == 'dump':
    write_data()
elif sys.argv[1] == 'vips':
    allow_additional_ips()
elif len(sys.argv) < 3:
    print_vms(sys.argv[1])
else:
    adjust_vm_count(sys.argv[1], int(sys.argv[2]))
