#!/bin/sh -eu

add_ssh_key() {
    vm_ip="$1"
    user="$2"

    pub_key_file="/opt/ica0002/data/students/$user/id_rsa.pub"
    if [ -f "$pub_key_file" ]; then
        echo "Reading $user SSH public from $pub_key_file..."
        key=$(cat "$pub_key_file")
    else
        echo "Retrieving $user SSH public key from GitHub..."
        key=$(curl -s "https://github.com/$user.keys" | sed "s/$/ $user/")
    fi

    if ! echo "$key" | grep -q '^ssh-'; then
        echo "ERROR Invalid SSH public key. Skipping $vm_ip..."
        return 1
    fi

    if ssh "$vm_ip" cat .ssh/authorized_keys | grep -q "$key"; then
        echo "$user public SSH key is already added to $vm_ip."
        echo "OK"
        return 0
    fi

    echo "Adding $user SSH public key to $vm_ip..."
    if ! ssh "$vm_ip" "echo '$key' >> .ssh/authorized_keys"; then
        echo "ERROR: Failed to add key."
        return 1
    fi

    echo "OK"
}

get_vms() {
    /usr/local/bin/vm-admin all | grep 192.168.42 | awk '{print $3":"$2}' | sed 's/-[0-9]*$//'
}

print_usage() {
    echo "$(basename $0) {<ip>|all}"
}


case "${1:-}" in
1*)
    add_ssh_key $(get_vms | grep "^$1" | head -1 | sed 's/:/ /')
    ;;
a*)
    for vm in $(get_vms); do
        echo ""
        echo "[$vm]"
        add_ssh_key $(echo $vm | sed 's/:/ /') || true
    done
    ;;
*)
    print_usage
    exit 1
    ;;
esac
