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

        if [ ! -f "$user_public_key_file" ]; then
            echo "Downloading public key for $user..."
            get_key "$user" > "$user_public_key_file"
        elif [ "$update_existing" = true ]; then
            echo "Updating public key for $user..."
            get_key "$user" > "$user_public_key_file"
        else
            echo "Public key file for $user is already downloaded."
        fi
    done
}

get_repos() {
    for repo in $@; do
        user=$(echo "$repo" | cut -d/ -f1)
        user_git_dir=$(user_dir "$user")/git

        if [ ! -d "$user_git_dir" ]; then
            echo "Cloning Git repository $repo..."
            git clone "git@github.com:$repo.git" "$user_git_dir"
            echo "---"
        elif [ "$update_existing" = true ]; then
            echo "Updating Git repository $repo..."
            cd "$user_git_dir"
            if git branch | grep -q .; then
                git checkout -- .
                git checkout master
                git pull origin master || true
            fi
            cd - > /dev/null
            echo "---"
        else
            echo "Git repository $repo is already cloned."
        fi
    done
}

print_usage() {
    echo "Usage: $(basename $0) {get|update} {keys|repos}"
}


case "${1:-}" in
g*) update_existing=false ;;
u*) update_existing=true ;;
*)
    print_usage
    exit 1
    ;;
esac

repos=$(cat "/opt/ica0002/data/ready-repos.txt")

case "${2:-}" in
k*) get_keys $repos ;;
r*) get_repos $repos ;;
*)
    print_usage
    exit 1
    ;;
esac

echo "All done."
