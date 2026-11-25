#!/bin/sh
set -eu

source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -gt 1 ]; then
    printf '%s\n' 'Usage: sh install-linux.sh [target_directory]' >&2
    exit 2
fi
target=${1:-"${XDG_DATA_HOME:-$HOME/.local/share}/pitranscriptor/app"}
parent=$(dirname -- "$target")
mkdir -p -- "$parent"
if [ -e "$target" ] || [ -L "$target" ]; then
    printf 'Destination already exists: %s\n' "$target" >&2
    exit 1
fi
mkdir -- "$target"
cp -R -- "$source_dir/Pitranscriptor/." "$target/"
chmod u+x "$target/Pitranscriptor"

if [ "$#" -eq 0 ]; then
    launcher_dir=${XDG_DATA_HOME:-$HOME/.local/share}/applications
    mkdir -p -- "$launcher_dir"
    absolute_target=$(CDPATH='' cd -- "$target" && pwd)
    executable=$(printf '%s' "$absolute_target/Pitranscriptor" | sed 's/[\\"`$]/\\&/g; s/%/%%/g')
    cat > "$launcher_dir/pitranscriptor.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Pitranscriptor
Comment=Local subtitle editor
Exec="$executable"
Terminal=false
Categories=AudioVideo;Video;
EOF
fi
printf 'Pitranscriptor: %s/Pitranscriptor\n' "$target"
