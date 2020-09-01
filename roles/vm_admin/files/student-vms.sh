#!/bin/sh -eu

if [ "$#" -lt 1 ]; then
    echo "Usage: $(basename $0) {0|1|2|3}"
    exit 1
fi

vm_count="$1"

for student in $(cat "/opt/ica0002/data/students-with-github-set-up.txt" | grep '.'); do
    if [ "$student" = "romankuchin" ]; then
        continue;
    fi
    echo "Provisioning $vm_count VMs for $student..."
    /usr/local/bin/vm-admin "$student" "$vm_count"
done
