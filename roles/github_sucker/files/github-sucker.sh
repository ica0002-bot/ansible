#!/bin/sh -eu

user_dir() {
    user_dir="/opt/ica0002/data/students/$1"
    test -d "$user_dir" || mkdir "$user_dir"
    echo "$user_dir"
}

get_key() {
    key=$(curl -s "https://github.com/$1.keys")
    echo "$key $1"
}

get_keys() {
    for repo in $@; do
        user=$(echo "$repo" | cut -d/ -f1)
        user_dir=$(user_dir "$user")
        user_public_key_file="$user_dir/id_rsa.pub"

        echo "Downloading public key for $user..."
        get_key "$user" > "$user_public_key_file"
    done
}

get_repos() {
    for repo in $@; do
        user=$(echo "$repo" | cut -d/ -f1)
        user_git_dir=$(user_dir "$user")/git

        needs_clone=true

        if [ -d "$user_git_dir/.git" ]; then
            echo "Updating Git repository $repo..."
            cd "$user_git_dir"
            git checkout -- . || true
            git checkout master || true
            if git pull origin master; then
                needs_clone=false
            else
                echo "Failed to merge changes -- wiping and cloning again..."
                cd /tmp
                rm -rf "$user_git_dir"
            fi
        fi

        if [ "$needs_clone" = true ]; then
            echo "Cloning Git repository $repo..."
            git clone "git@github.com:$repo.git" "$user_git_dir"
        fi

        echo "---"
    done
}

print_usage() {
    echo "Usage: $(basename $0) {keys|repos}"
}


repos=$(cat "/opt/ica0002/data/ready-repos.txt")

case "${1:-}" in
k*) get_keys $repos ;;
r*) get_repos $repos ;;
*)
    print_usage
    exit 1
    ;;
esac

echo "All done."
