#!/bin/sh -eu

expected_files=$(cat <<EOF
ansible.cfg:lab-1,lab-2,lab-3,lab-4
group_vars/all.yaml:lab-4
hosts:lab-1,lab-2,lab-3,lab-4
lab02_web_server.yaml:lab-2
lab03_web_app.yaml:lab-3
lab04_web_app.yaml:lab-4
lab05_dns.yaml:lab-5
roles/agama/tasks/main.yaml:lab-3
roles/bind/tasks/main.yaml:lab-5
roles/nginx/tasks/main.yaml:lab-2,lab-3
roles/users/tasks/main.yaml:lab-2
roles/uwsgi/tasks/main.yaml:lab-3
roles/mysql/tasks/main.yaml:lab-4
EOF
)

check_student() {
    student="$1"

    labs_not_done=""
    repo="/opt/ica0002/data/students/$student/git"
    result=true

    html=$(cat <<EOF
<html>
    <head>
        <title>$student - ICA0002 2020</title>
        <link rel="stylesheet" type="text/css" href="/style.css">
    </head>
    <body>
        <a href="/">ICA0002 2020</a> &raquo; <a href="/students.html">Students</a> &raquo; <a href="/results/$student.html">$student</a>
        <h1>$student</h1>
        <p>Checks:</p>
        <ul>
EOF
    )
    echo "---"
    echo "Student: $student"

    # Check repository
    if grep -q "^$student/" /opt/ica0002/data/ready-repos.txt; then
        html="$html\n$(html_ok GitHub repository is set up correctly.)"
        print_ok "GitHub repository is set up correctly"
    else
        html="$html\n$(html_fail GitHub repository is not ready: either not private or public key missing.)"
        print_fail "GitHub repository is not ready: either not private or public key missing"
        result=false
    fi

    # Check files
    if [ -d "$repo" ]; then
        for f in $expected_files; do
            file=$(echo "$f" | cut -d: -f1)
            labs=$(echo "$f" | cut -d: -f2)
            if [ -f "$repo/$file" ]; then
                html="$html\n"$(html_ok "<code>$file</code> found.")
                print_ok "$file found"
            else
                labs_formatted=$(format_lab_list "$labs")
                html="$html\n"$(html_fail "<code>$file</code> is missing; labs not accepted: $labs_formatted.")
                print_fail "$file is missing; labs not accepted: $labs_formatted"
                labs_not_done="$labs_not_done,$labs"
                result=false
            fi
        done
    else
        html="$html\n"$(html_fail "Could not check your repository at this time. Please re-check this page tomorrow. If there are still no results, please contact the teachers.")
        result=false
        print_fail "Local repository not found: $repo"
    fi

    html="$html\n</ul>\n"

    # Print summary
    if [ "$result" = true ]; then
        html="$html\n<p>All good do far.</p>"
        echo "All good."
    else
        html="$html\n<p>A few problems found.</p>"
        echo "A few problems found."
    fi

    if [ -n "$labs_not_done" ]; then
        labs_formatted=$(format_lab_list $labs_not_done)
        html="$html\n<p>Labs not accepted: $labs_formatted.</p>"
        echo "Labs not accepted: $labs_formatted"
    fi

    html="$html\n<p>Last checked on $(date +'%b %d at %R UTC').</p>\n</body></html>"
    echo "$html" > "/opt/ica0002/pub/results/$student.html"
}

html_fail() {
    echo "<li><span class=\"fail\">Problem</span>: $@</li>"
}

html_ok() {
    echo "<li><span class=\"ok\">Ok</span>: $@</li>"
}

format_lab_list() {
    echo "$@" | sed 's/lab-//g;' | tr -d ' ' | xargs -d, -n1 | sort -u | grep . | paste -sd, | sed 's/,/, /g'
}

print_fail() {
    echo " [\033[0;31mfail\033[0m] $@"
}

print_ok() {
    echo " [\033[0;32mok\033[0m] $@"
}


for i in $(cat /opt/ica0002/data/known-students.txt); do
    check_student "$i"
done
