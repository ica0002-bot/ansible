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


def get_vms():
    vms = []
    vms_with_keys = []

    print('Retrieving SSH key info...')
    with open('/opt/ica0002/data/vms-with-student-key-added.txt') as f:
        raw_vm_list = f.readlines()
    for vm in raw_vm_list:
        vms_with_keys.append(vm.strip().split(':')[0])

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
        if ip in vms_with_keys:
            public_ssh = 'ubuntu@%s:%s22' % (vm1_public_ip, vm_id)
        else:
            public_ssh = 'student_key_not_added_yet'

        vms.append({
            'description': vm['description'],
            'ip': ip,
            'name': vm['name'],
            'public_ssh': public_ssh,
            'public_url': 'http://%s:%s80' % (vm1_public_ip, vm_id),
            'uuid': vm['uuid'],
        })

    return vms


def group_vms_by_student(vms):
    student_vms = {}

    for vm in vms:
        student = vm['description']
        if not student in student_vms:
            student_vms[student] = []
        student_vms[student].append(vm)

    print('Retrieving student info...')
    with open('/opt/ica0002/data/students-with-github-set-up.txt') as f:
        raw_students = f.readlines()
    for raw_student in raw_students:
        student = raw_student.strip()
        if not student in student_vms:
            student_vms[student] = []

    return student_vms


def print_vms(vms, student='all'):
    student_vms = group_vms_by_student(vms)
    for s in sorted(student_vms.keys()):
        if student not in ['all', s]:
            continue

        heading = '\nStudent %s VMs:' % s
        if not student_vms[s]:
            print('%s none' % heading)
            continue

        print(heading)
        for vm in student_vms[s]:
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
            'flavor': 'https://api.etais.ee/api/openstacktenant-flavors/fa67a49065274d3e8b6b1dcf80130236/',
            'ssh_public_key': 'https://api.etais.ee/api/keys/6ecc7a9f69514c49b076d68245ac66b5/',
            'security_groups': [{
                'url': 'https://api.etais.ee/api/openstacktenant-security-groups/70bdb790eb854be6b596bfdf4a4a572d/',
            }],
            'internal_ips_set': [{
                'subnet': 'https://api.etais.ee/api/openstacktenant-subnets/850dbada4f1443abac5b10ce5bf3cfbc/',
            }],
            'floating_ips': [],
            'system_volume_size': 10240,
            'system_volume_type': 'https://api.etais.ee/api/openstacktenant-volume-types/c388cd0b264c4878a97c1a175d4eef9c/',
            'data_volume_type': 'https://api.etais.ee/api/openstacktenant-volume-types/c388cd0b264c4878a97c1a175d4eef9c/',
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


def adjust_vm_count(vms, student, vm_count):
    if not 0 <= vm_count <= 3:
        print('ERROR: allowed VM counts are 0, 1, 2 and 3.')
        sys.exit(1)

    student_vms = group_vms_by_student(vms)
    student_list = []
    if student == 'all':
        student_list += sorted(student_vms.keys())
    else:
        student_list.append(student)

    for s in student_list:
        actual_vm_count = 0
        if s in student_vms:
            actual_vm_count = len(student_vms[s])
        diff = abs(actual_vm_count - vm_count)

        print('Student %s has %d VMs, desired: %d' % (s, actual_vm_count, vm_count))
        if actual_vm_count > vm_count:
            for i in range(int(vm_count), actual_vm_count):
                print('Deleting VM %s...' % student_vms[s][i]['name'])
                delete_vm(student_vms[s][i]['uuid'])
        elif actual_vm_count < vm_count:
            for i in range(actual_vm_count, int(vm_count)):
                create_vm(s, i + 1)

    print('All good.')


def print_help():
    print('''Usage: %s <options>

      Options:
        dump                    - generate HTML page
        <student_name|all>      - print list of VMs for given student or everybody
        <student_name|all> <n>  - create/delete VMs for given student or everybody''' % sys.argv[0])


def write_data(vms):
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
                </tr>
    '''

    total_vm_count = 0
    ready_vm_count = 0

    student_vms = group_vms_by_student(vms)
    students = sorted(student_vms.keys())
    for student in students:
        vm_ips = []
        vm_names = []
        vm_ssh_logins = []
        vm_urls = []

        for vm in student_vms[student]:
            vm_ips.append(vm['ip'])
            vm_names.append(vm['name'])
            vm_urls.append('<a href="%s">%s</a>' % (vm['public_url'], vm['public_url']))

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
        html += '</tr>'

    html += '''
                <tr><th colspan="5">Total: %d &nbsp; &middot; &nbsp; Ready: %d</th></tr>
            </table>
            <div class="footer">
                Updated every 15 minutes. Last checked on %s.
                <br><br>
                Missing VMs are ususally added within 6 hours after your GitHub repository is set up.
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

    with open('/opt/ica0002/data/students-with-vms.txt', 'w') as f:
        f.write('\n'.join(students) + '\n')


if len(sys.argv) <= 1:
    print_help()
    sys.exit(1)

vms = get_vms()

if sys.argv[1] == 'dump':
    write_data(vms)
elif len(sys.argv) == 2:
    print_vms(vms, student=sys.argv[1])
else:
    for s in sys.argv[1].split(','):
        if s:
            adjust_vm_count(vms, s, int(sys.argv[2]))
