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


def extract_student_vms(vms, student):
    student_vms = []

    for vm in vms:
        if vm['description'] == student:
            student_vms.append(vm)

    return student_vms


def extract_students(vms):
    students = []

    for vm in vms:
        if not vm['description'] in students:
            students.append(vm['description'])

    return sorted(students)


def get_vms():
    vms = []

    print('Retrieving list of VMs from Waldur...')
    r = requests.get('%s/openstacktenant-instances/?project=%s' % (base_url, project_id), headers=headers)
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
            'description': vm['description'],
            'ip': ip,
            'name': vm['name'],
            'public_ssh': 'ubuntu@%s:%s22' % (vm1_public_ip, vm_id),
            'public_url': 'http://%s:%s80' % (vm1_public_ip, vm_id),
            'uuid': vm['uuid'],
        })

    return vms


def print_vms(vms, student='all'):
    students = extract_students(vms) if student == 'all' else [student]
    for student in students:
        student_vms = extract_student_vms(vms, student)
        print('\nStudent %s VMs:' % student)
        for vm in student_vms:
            print('  - %s  %s  %s  %s' % (vm['name'], vm['ip'], vm['public_ssh'], vm['public_url']))


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
    requests.post('%s/marketplace-cart-items/' % base_url, headers=headers, data=json.dumps(payload))

    payload = {
        'project': 'https://api.etais.ee/api/projects/%s/' % project_id,
    }
    requests.post('%s/marketplace-cart-items/submit/' % base_url, headers=headers, data=json.dumps(payload))


def delete_vm(vm_id):
    requests.delete('%s/openstacktenant-instances/%s/force_destroy/?delete_volumes=true&release_floating_ips=true' % (base_url, vm_id), headers=headers)


def adjust_vm_count(vms, student, vm_count):
    if not 0 <= vm_count <= 3:
        print('ERROR: allowed VM counts are 0, 1, 2 and 3.')
        sys.exit(1)

    student_vms = extract_student_vms(vms, student)
    actual_vm_count = len(student_vms)
    diff = abs(actual_vm_count - vm_count)

    print('Student %s has %d VMs, desired: %d' % (student, actual_vm_count, vm_count))
    if actual_vm_count > vm_count:
        for i in range(int(vm_count), actual_vm_count):
            print('Deleting VM %s...' % student_vms[i]['name'])
            delete_vm(student_vms[i]['uuid'])
    elif actual_vm_count < vm_count:
        for i in range(actual_vm_count, int(vm_count)):
            create_vm(student, i + 1)

    print('All good.')


def print_help():
    print('''Usage: %s <options>

      Options:
        all                 - print all known student VMs
        dump                - generate HTML page
        <student_name>      - print list of VMs for given student
        <student_name> <n>  - create/delete VMs for given student''' % sys.argv[0])


def write_data(vms):
    html = '''
    <html>
        <head>
            <meta http-equiv="refresh" content="30">
            <title>VMs - ICA0002 2020</title>
            <link rel="stylesheet" type="text/css" href="style.css">
        </head>
        <body>
            <h1><a href="/">ICA0002 2020</a> &raquo; VMs</h1>
            <table>
                <tr>
                    <th>GitHub user</th>
                    <th>VM names</th>
                    <th>VM IPs</th>
                    <th>Public SSH</th>
                    <th>Public URLs</th>
                </tr>
    '''

    students = extract_students(vms)
    for student in students:
        vm_ips = []
        vm_names = []
        vm_ssh_ports = []
        vm_urls = []
        student_vms = extract_student_vms(vms, student)
        for vm in student_vms:
            vm_ips.append(vm['ip'])
            vm_names.append(vm['name'])
            vm_ssh_ports.append(vm['public_ssh'].replace(':', '&nbsp;port&nbsp;'))
            vm_urls.append('<a href="%s">%s</a>' % (vm['public_url'], vm['public_url']))

        html += '<tr>'
        html += '<td><a href="https://github.com/%s">%s</a></td>' % (student, student)
        html += '<td>%s</td>' % ('<br>'.join(vm_names))
        html += '<td>%s</td>' % ('<br>'.join(vm_ips))
        html += '<td>%s</td>' % ('<br>'.join(vm_ssh_ports))
        html += '<td>%s</td>' % ('<br>'.join(vm_urls))
        html += '</tr>'

    html += '''
            </table>
            <div class="footer">Last checked on %s.</div>
        </body>
    </html>
    ''' % time.strftime('%b %d at %H:%M %Z')

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
    adjust_vm_count(vms, sys.argv[1], int(sys.argv[2]))
