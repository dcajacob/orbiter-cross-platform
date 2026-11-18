# Phase 8 release checklist

The four preview runtime packages, stock data installer, and four matching SDKs
have passed their scoped checks. All nine retained deliverables matched their
published or recorded SHA-256 hashes during release preflight. These records
identify the exact packages and source revisions tested.
[Packages](Phase8Packages.md) · [Stock data installer](Phase8StockData.md) · [SDKs](Phase8SDK.md)

## Work available during the hold

| Item | Preflight finding and remaining work |
| --- | --- |
| Linux support floor | The Ubuntu 24.04 runtime, stock installer, and matching SDK passed the short checks on a separate Ubuntu 24.04 runner. Keep that baseline when building and qualifying the final release candidate. [Linux compatibility evidence](Linux24Compatibility.md) |
| Writable user data | The native installer creates a separate `user/` tree. The Windows preview keeps `Orbiter.cfg` and saved scenarios under `runtime/`. Check the final install with read-only program and data trees, and verify settings, saves, logs, and caches go to writable user locations independently of the working directory. |
| Dependency notices | The inspected previews ship Qt libraries and plug-ins on Windows and macOS. The archives carry Orbiter and several dependency notices. The inventory found no separate Qt license or notice file. Complete the notices and source information against the exact deployed Qt 6.8.3 components and review the other bundled dependencies and data terms. [Qt 6.8 licensing](https://doc.qt.io/qt-6.8/licensing.html) |
| Distribution and support | Prepare release notes, installation instructions, and the supported OS, toolchain, and module matrix. Document that Windows supports the classic SDK and the tested native SDKs retain their existing stock-class admission rules. The Mac previews are ad-hoc signed. For direct public Mac distribution, prepare Developer ID signing, notarization, and a clean Gatekeeper check of the final archives. [Apple distribution guidance](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) |
| Release candidate and evidence | Reconcile the tested source revisions and qualification branches into the intended release candidate. Create a manifest for the final runtime, SDK, installer, and data identities, and retain the completed acceptance evidence in durable storage. The preview hashes remain evidence for those preview bytes. |

The preview archive inventory found Qt Core, Gui, Svg, and Widgets on both
Windows and macOS. Windows also ships Qt Network and macOS ships Qt DBus.
The archive inventories include their deployed platform and image plug-ins.

## Final acceptance

- Freeze the final candidate and close the remaining [Phase 6 gates](Phase6Closeout.json).
  The ledger still has open stock admission, named workflows, lifecycle/input,
  and acceptance evidence. The full 157-scenario startup sweep, named missions,
  and remaining native/current Windows parity checks belong to that qualification.
- Complete the required local operator, hardware, and performance checks on
  the release candidate. Windows hands-on stays on hold. Hosted software graphics
  provide smoke evidence, and the earlier Linux controller session remains
  evidence for the build tested in that session.

The full runs and Windows hands-on check remain on hold. The production
[release criteria](README.md#production-references-and-acceptance-contracts)
define the performance, behavior, and evidence requirements for closeout.
