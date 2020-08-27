#!/usr/bin/env python3

import json
import requests
import sys
import time


with open('/root/.waldur-api-token') as f:
    token = f.readlines()[0].strip()

headers = {
    "Authorization": "token %s" % token,
    "Content-Type": "application/json"
}
base_url = 'https://api.etais.ee/api'
r = requests.get('%s/openstacktenant-instances/?project=22d7e03a0d654f98bd45cafd592ce8a2' % base_url, headers=headers)
raw_vm_list = r.json()


def get_student_vms(student):
    print('Student: %s' % student)
    student_vms = []
    for vm in raw_vm_list:
        if vm['description'] == student and 'internal_ips' in vm:
            student_vms.append(','.join(vm['internal_ips']))
    print('VMs: %s' % ','.join(student_vms))


def create_vm(student, id):
    payload = {
        "offering": "https://api.etais.ee/api/marketplace-offerings/b8a3f21d92d9411a89315ab727340471/",
        "project": "https://api.etais.ee/api/projects/22d7e03a0d654f98bd45cafd592ce8a2/",
        "attributes": {
            "name": "%s-%s" % (student, id),
            "description": "%s" % student,
            "image": "https://api.etais.ee/api/openstacktenant-images/7054bc7140894afc91af6b84c13a3798/",
            "flavor": "https://api.etais.ee/api/openstacktenant-flavors/fa67a49065274d3e8b6b1dcf80130236/",
            "ssh_public_key": "https://api.etais.ee/api/keys/c630a307be5b4b9a988afac723ea1a0b/",
            "security_groups": [{"url":"https://api.etais.ee/api/openstacktenant-security-groups/70bdb790eb854be6b596bfdf4a4a572d/"}],
            "internal_ips_set": [{"subnet":"https://api.etais.ee/api/openstacktenant-subnets/850dbada4f1443abac5b10ce5bf3cfbc/"}],
            "floating_ips":[],
            "system_volume_size": 10240,
            "system_volume_type": "https://api.etais.ee/api/openstacktenant-volume-types/c388cd0b264c4878a97c1a175d4eef9c/",
            "data_volume_type": "https://api.etais.ee/api/openstacktenant-volume-types/c388cd0b264c4878a97c1a175d4eef9c/"
        }
    }
    r = requests.post('%s/marketplace-cart-items/' % base_url, headers=headers, data=json.dumps(payload))
    print(r.json())
    payload = {
        "project": "https://api.etais.ee/api/projects/22d7e03a0d654f98bd45cafd592ce8a2/"
    }
    r = requests.post('%s/marketplace-cart-items/submit/' % base_url, headers=headers, data=json.dumps(payload))
    print(r.json())


def delete_vm(vm_id):
    r = requests.delete('%s/openstacktenant-instances/%s/force_destroy/?delete_volumes=true&release_floating_ips=true' % (base_url, vm_id), headers=headers)


def adjust_student_vms(student, vm_count):
    student_vms = []
    for vm in raw_vm_list:
        if vm['description'] == student:
            student_vms.append(vm)
    print('Student %s has %d VMs, desired: %d' % (student, len(student_vms), vm_count))
    if len(student_vms) == vm_count:
        print('Ok')
    if len(student_vms) > vm_count:
        print('Deleting %d VMs' % (len(student_vms) - int(vm_count)))
        for i in range(int(vm_count), len(student_vms)):
            print('Deleting %s' % student_vms[i]['name'])
            delete_vm(student_vms[i]['uuid'])
    if len(student_vms) < vm_count:
        print('Creating %d VMs' % (int(vm_count) - len(student_vms)))
        for i in range(len(student_vms) + 1, int(vm_count) + 1):
            create_vm(student, i)


def print_help():
    print('''Usage:
        html - generate html page
        <student_name> - print list of VMs for given student
        <student_name> <n> - crete/delete VMs for given student''')


def generate_html():
    student_list = []
    for vm in raw_vm_list:
        if not vm['description'] in student_list and vm['description']:
            student_list.append(vm['description'])
    # Compose HTML
    html = '''
    <html>
        <head>
            <meta http-equiv="refresh" content="30">
            <title>ICA0002 VMs</title>
            <link rel="stylesheet" type="text/css" href="style.css">
        </head>
        <body>
            <h1>ICA0002 VMs</h1>
            <table>
                <tr>
                    <th>GitHub user</th>
                    <th>VM IPs</th>
                </tr>
    '''
    for student in student_list:
        student_ips = []
        for vm in raw_vm_list:
            if student == vm['description'] and 'internal_ips' in vm:
                student_ips.append(','.join(vm['internal_ips']))
        html += '<tr>'
        html += '<td>%s</td>' % (student)
        html += '<td>%s</td>' % (','.join(student_ips))
        html += '</tr>'
    html += '''
            </table>
            <div class="footer">Last checked on %s.</div>
        </body>
    </html>
    ''' % time.strftime('%b %d at %H:%M %Z')
    with open('/opt/ica0002/pub/vms.html', 'w') as f:
        f.write(html)


if len(sys.argv) > 1:
    if sys.argv[1] == 'html':
        generate_html()
    elif len(sys.argv) == 2:
        get_student_vms(sys.argv[1])
    elif len(sys.argv) == 3:
        adjust_student_vms(sys.argv[1], int(sys.argv[2]))
    else:
        print_help()
else:
    print_help()
