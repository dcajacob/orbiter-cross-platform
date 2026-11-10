#!/usr/bin/env bash
set -euo pipefail
# Retain signed dated-snapshot metadata; use only identical SHA256-bound Ubuntu pool blobs.
parse_plan() {
  local plan="$1" destination="$2" line uri filename bytes hash extra relative
  test ! -e "$destination"
  : > "$destination"
  while IFS= read -r line; do
    case "$line" in "'"*) ;; *) continue ;; esac
    read -r uri filename bytes hash extra <<< "$line"
    test -z "${extra:-}"
    [[ "$uri" == "'https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/"*"'" ]]
    uri="${uri:1:${#uri}-2}"
    [[ "$uri" != *'..'* && "$uri" != *'\'* ]]
    [[ "$filename" =~ ^[-A-Za-z0-9+_.%:~]+\.deb$ && "$filename" != .* && "$filename" != */* ]]
    [[ "$bytes" =~ ^[1-9][0-9]{0,10}$ && "$bytes" -lt 2147483648 ]]
    [[ "$hash" =~ ^SHA256:[0-9a-f]{64}$ ]]
    relative="${uri#https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/}"
    printf '%s\t%s\t%s\t%s\t%s\n' "$uri" "https://archive.ubuntu.com/ubuntu/$relative" "$filename" "$bytes" "${hash#SHA256:}" >> "$destination"
  done < "$plan"
  test -s "$destination"
  test "$(cut -f3 "$destination" | sort -u | wc -l)" -eq "$(wc -l < "$destination")"
}
if [[ "${1:-}" == --validate-plan-only ]]; then
  test "$#" -eq 3
  parse_plan "$2" "$3"
  exit 0
fi

test "${GITHUB_ACTIONS:-}" = true
test "${RUNNER_OS:-}" = Linux
case "${PROFILE:-}" in Debug-automatic|Debug-sse2|Release-automatic|Release-sse2) ;; *) exit 2;; esac
export DEBIAN_FRONTEND=noninteractive
output="out/original-package-official-pool/$PROFILE"
test ! -e "$output"
mkdir -p "$output"
trap 'code=$?; printf "%s\n" "$code" > "$output/terminal-exit-code.txt"' EXIT
inventory=out/hosted-native-providers/system-packages.txt
test "$(sha256sum "$inventory" | cut -d' ' -f1)" = 0ae6765d460a0d744c48afdb242257d02a29da4845cf7e8b7fda42004e164900
mapfile -t pins < "$inventory"
test "${#pins[@]}" -eq 488
cp "$inventory" "$output/original-system-packages.txt"
configs=(/etc/apt/apt.conf.d/99-orbiter-ci-https /etc/apt/apt.conf.d/99-orbiter-class-snapshot /run/orbiter-ci-system-ca.pem)
for path in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do
  test -f "$path" || continue
  configs+=("$path")
done
sha256sum "${configs[@]}" > "$output/original-archive-config-before.sha256"
mkdir -p "$output/archive-config"
for path in "${configs[@]}"; do name="${path#/}"; cp "$path" "$output/archive-config/${name//\//__}"; done
run_stage() {
  local label="$1" code
  shift
  printf '%q ' "$@" > "$output/$label.argv.txt"
  printf '\n' >> "$output/$label.argv.txt"
  set +e
  "$@" > "$output/$label.log" 2>&1
  code=$?
  set -e
  printf '%s\t%s\t%s\n' "$label" "$code" "$(date -u --iso-8601=seconds)" >> "$output/commands.tsv"
  if [[ "$code" -ne 0 ]]; then tail -n 100 "$output/$label.log"; return "$code"; fi
}
run_stage original-signed-snapshot-update apt-get update
run_stage original-pinned-URI-plan apt-get -o Acquire::ForceHash=sha256 --print-uris --yes --download-only --no-install-recommends install "${pins[@]}"
parse_plan "$output/original-pinned-URI-plan.log" "$output/exact-original-plan.tsv"
mkdir -p "$output/signed-metadata"
for path in /var/lib/apt/lists/*_InRelease /var/lib/apt/lists/*_Release /var/lib/apt/lists/*_Release.gpg /var/lib/apt/lists/*_Packages*; do
  test -f "$path" || continue
  cp "$path" "$output/signed-metadata/$(basename "$path")"
done
cp /usr/share/keyrings/ubuntu-archive-keyring.gpg "$output/signed-metadata/ubuntu-archive-keyring.gpg"
count=0
while IFS=$'\t' read -r original mirror filename bytes expected; do
  count=$((count+1))
  cache="/var/cache/apt/archives/$filename"
  test ! -L "$cache"
  run_stage "exact-official-blob-$count" /usr/lib/apt/apt-helper -o Acquire::ForceHash=sha256 download-file "$mirror" "$cache" "SHA256:$expected"
  test "$(stat -c '%s' "$cache")" -eq "$bytes"
  actual="$(sha256sum "$cache" | cut -d' ' -f1)"
  test "$actual" = "$expected"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$original" "$mirror" "$filename" "$bytes" "$expected" "$actual" >> "$output/independently-verified-original-blobs.tsv"
done < "$output/exact-original-plan.tsv"
test "$count" -gt 0
run_stage install-only-exact-verified-cache apt-get --no-download install -y --no-install-recommends "${pins[@]}"
dpkg-query -W '-f=${binary:Package}=${Version}\n' > "$output/actual-system-packages.txt"
cmp "$inventory" "$output/actual-system-packages.txt"
sha256sum --check "$output/original-archive-config-before.sha256" > "$output/original-archive-config-after-verification.txt"
printf '%s\n' prepared-exact-original-package-inventory-only-not-qualified > "$output/status.txt"
