#!/usr/bin/env bash
set -euo pipefail
# Transport repair only: retain the same signed Ubuntu archives, suites and exact package versions.
test "${GITHUB_ACTIONS:-}" = true
test "${RUNNER_OS:-}" = Linux
case "${PROFILE:-}" in Debug-automatic|Debug-sse2|Release-automatic|Release-sse2) ;; *) exit 2;; esac
case "${1:-}" in Tests/Production/Closeout/prepare_hosted_class_rejections.sh|Tests/Production/Closeout/prepare_hosted_class_userspace.sh) ;; *) exit 2;; esac
ca=/run/orbiter-ci-system-ca.pem
test -s "$ca"
output="out/native-rejection-network/$PROFILE"
test ! -e "$output"
mkdir -p "$output"
sha256sum "$ca" > "$output/system-trust.sha256"
rewrite_source() {
  local input="$1" target="$2"
  sed -e 's#http://archive.ubuntu.com/ubuntu#https://archive.ubuntu.com/ubuntu#g' \
      -e 's#http://security.ubuntu.com/ubuntu#https://security.ubuntu.com/ubuntu#g' \
      "$input" > "$target"
  # Compare canonical forms to permit already-HTTPS inputs without changing any other field.
  sed -e 's#https://archive.ubuntu.com/ubuntu#http://archive.ubuntu.com/ubuntu#g' \
      -e 's#https://security.ubuntu.com/ubuntu#http://security.ubuntu.com/ubuntu#g' \
      "$input" > "$target.before-canonical"
  sed -e 's#https://archive.ubuntu.com/ubuntu#http://archive.ubuntu.com/ubuntu#g' \
      -e 's#https://security.ubuntu.com/ubuntu#http://security.ubuntu.com/ubuntu#g' \
      "$target" > "$target.after-canonical"
  cmp "$target.before-canonical" "$target.after-canonical"
}
count=0
for source in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do
  test -f "$source" || continue
  name=$(basename "$source")
  cp "$source" "$output/$name.before"
  rewrite_source "$output/$name.before" "$output/$name.after"
  cp "$output/$name.after" "$source"
  count=$((count+1))
done
test "$count" -gt 0
cat > /etc/apt/apt.conf.d/99-orbiter-ci-https <<'APT'
Acquire::https::CaInfo "/run/orbiter-ci-system-ca.pem";
Acquire::Retries "3";
Acquire::https::Timeout "30";
APT::Update::Error-Mode "any";
APT
cp /etc/apt/apt.conf.d/99-orbiter-ci-https "$output/apt-transport.conf"
# Official dated archive support: https://snapshot.ubuntu.com/
# Last successful complete original inventory restore; all versions stay fixed.
cat > /etc/apt/apt.conf.d/99-orbiter-class-snapshot <<'APT'
APT::Snapshot "20261109T212432Z";
APT
cp /etc/apt/apt.conf.d/99-orbiter-class-snapshot "$output/archive-snapshot.conf"
apt-config dump > "$output/actual-apt-config.txt"
# Use the standard runner's read-only system CA bundle; certificate and archive signature checks stay enabled.
exec bash "$1"
