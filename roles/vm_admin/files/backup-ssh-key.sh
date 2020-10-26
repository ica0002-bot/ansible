#!/bin/sh -eu

backup_server=192.168.42.39


add_ssh_key() {
    vm_ip="$1"
    user="$2"

    print_info "Retrieving backup SSH key from $vm_ip..."
    pub_key_file="/home/backup/.ssh/id_rsa.pub"
    key=$(ssh "$vm_ip" sudo -hlocalhost cat "$pub_key_file")
    if [ -z "$key" ]; then
        print_error "SSH key not found on $vm_ip in $pub_key_file."
        return 1
    fi

    if ! ssh "$backup_server" id "$user" >/dev/null 2>&1; then
        print_info "User $user not found on the backup server -- creating..."
        ssh "$backup_server" "
            sudo -hlocalhost useradd -m '$user'
            sudo -hlocalhost -u'$user' mkdir '/home/$user/.ssh'
        "
    fi

    print_info "Authorizing $vm_ip backup SSH key on the backup server..."
    if ! ssh "$backup_server" "echo '$key' | sudo -u'$user' tee -a /home/$user/.ssh/authorized_keys"; then
        print_error "Failed to add key."
        return 1
    fi

    print_info "OK"
}

get_vms() {
    /usr/local/bin/vm-admin all | grep 192.168.42 | awk '{print $3":"$2}' | sed 's/-[0-9]*$//'
}

print_error() {
    echo "ERROR: $1" >&2
}

print_info() {
    echo "$1" >&2
}


print_usage() {
    echo "$(basename $0) {<ip>|all}"
}


print_info "Backup server: $backup_server"

if ! ssh "$backup_server" hostname | grep -q '^vm2$'; then
    print_error "Backup server hostname is not vm2. Something's fishy..."
    exit 1
fi

case "${1:-}" in
1*)
    vm=$(get_vms | grep "^$1" | head -1)
    add_ssh_key $(echo $vm | sed 's/:/ /')
    ;;
a*)
    for vm in $(get_vms); do
        print_info ""
        print_info "[$vm]"
        add_ssh_key $(echo $vm | sed 's/:/ /') || true
    done
    ;;
*)
    print_usage
    exit 1
    ;;
esac
