#!/bin/sh -eu

vms_file="/opt/ica0002/data/ready-vms.txt"


add_ssh_key() {
    vm_ip="$1"
    user="$2"

    pub_key_file="/opt/ica0002/data/students/$user/id_rsa.pub"
    if [ -f "$pub_key_file" ]; then
        print_info "Reading $user SSH public from $pub_key_file..."
        key=$(cat "$pub_key_file")
    else
        print_info "Retrieving $user SSH public key from GitHub..."
        key=$(curl -s "https://github.com/$user.keys" | sed "s/$/ $user/")
    fi

    if ! echo "$key" | grep -q '^ssh-'; then
        print_error "Invalid SSH public key. Skipping $vm_ip..."
        return 1
    fi

    ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$vm_ip"

    if ssh "$vm_ip" cat .ssh/authorized_keys | grep -q "$key"; then
        print_info "$user public SSH key is already added to $vm_ip."
    else
        echo "Adding $user SSH public key to $vm_ip..."
        if ! ssh "$vm_ip" "echo '$key' >> .ssh/authorized_keys"; then
            print_error "Failed to add key."
            return 1
        fi
    fi

    result="$vm_ip:$user"

    test -f "$vms_file" || touch "$vms_file"
    if grep -q "^$vm_ip:" "$vms_file"; then
        sed -i "s/^$vm_ip:.*/$result/" "$vms_file"
    else
        echo "$result" >> "$vms_file"
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


case "${1:-}" in
1*)
    vm=$(get_vms | grep "^$1:" | head -1)
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
