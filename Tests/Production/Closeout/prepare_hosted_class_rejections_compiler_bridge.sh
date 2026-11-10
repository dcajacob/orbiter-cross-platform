#!/usr/bin/env bash
set -euo pipefail
# Only transport changes: restore all488 exact original packages before unchanged SDK/collector setup.
source_output="out/class-rejection-official-pool-source/$PROFILE"
test ! -e "$source_output"
mkdir -p "$source_output"
sha256sum Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh \
  Tests/Production/Closeout/prepare_hosted_class_rejections_official_pool_network.sh \
  Tests/Production/Closeout/prepare_hosted_class_rejections_official_pool.sh \
  Tests/Production/Closeout/prepare_hosted_class_rejections_sdk.sh \
  Tests/Production/Closeout/hosted_class_rejections_sdk.py \
  Tests/Production/Closeout/hosted_class_rejections.py \
  Tests/Production/Closeout/rejection_fixture_compiler_bridge.py \
  Tests/Production/Closeout/prepare_hosted_class_rejections_compiler_bridge_network.sh \
  Tests/Production/Closeout/prepare_hosted_class_rejections_compiler_bridge.sh > "$source_output/before.sha256"
bash Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh
python3 -B Tests/Production/Closeout/rejection_fixture_compiler_bridge.py install --profile "$PROFILE"
bash Tests/Production/Closeout/prepare_hosted_class_rejections_sdk.sh
sha256sum --check "$source_output/before.sha256" > "$source_output/after-verification.txt"
