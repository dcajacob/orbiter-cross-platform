#!/usr/bin/env bash
set -euo pipefail
bash Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh
# The unchanged original preflight still verifies all488 versions, signed metadata and TLS.
exec bash Tests/Production/Closeout/prepare_hosted_class_rejection_userspace.sh
