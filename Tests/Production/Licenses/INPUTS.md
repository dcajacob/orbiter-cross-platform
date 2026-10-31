# Preserved production inputs

These packages are independent of this repository's MIT-licensed source.
They are archived unchanged for this project's non-commercial verification.
No package executable is used in place of the source-built application.

* `Orbiter2016.zip`: publisher Martin Schweiger, Orbiter 2016 core ZIP edition.
  The **Orbiter Freeware License**, section 28.1 of `Doc/Orbiter.pdf`, printed
  page 143, permits use, copying and distribution without fee for personal,
  educational, charity and other non-commercial use subject to its conditions.
  These include preserving binary code, notices and identifying elements,
  restrictions on sales/cost recovery and promotion, and disclosure of modules
  using undocumented interfaces. The warranty disclaimer continues on page 144.
  The original manual and readme accompany the intact publisher package. The
  archive is split only at byte boundaries to meet GitHub's per-asset limit;
  concatenate numbered parts in order and verify the complete SHA256 before
  extraction. This does not change any archive member. The tests take only the
  28 locked standard planet archives; they never take 2016 binaries/ephemerides.
* `Orbiter-x64.zip`: the pinned orbitersim/orbiter package listed in
  `stock-data.lock.json`. Its original MIT `LICENSE` and readme are included
  separately and remain in the intact package. Third-party component notices
  remain in that archive and the corresponding source. Do not infer that the
  separate 2016 package has the same license.
* SPICE: NASA/JPL/NAIF and the teams that produced the source data are credited.
  The Orbiter kernel is preserved without modification. The SPICE library is
  part of the Orbiter application, not offered here as a standalone toolkit
  mirror. See [NAIF redistribution rules](https://naif.jpl.nasa.gov/naif/rules.html).

`inputs.json` records the original URLs, sizes, complete-package hashes, ordered
part hashes and notice hashes. The two profile locks record each consumed data
file. The source revision and tool/runtime dependency manifests are separate.
This storage is test provisioning; it is not the final Linux asset installer.

The manual was inspected from the original ZIP, including a rendered inspection
of printed page 143. Its original bytes are retained; extracted text is not a
replacement for the publisher's terms. Neither package's data is relicensed.

GitHub's documented limit is less than 2 GiB per release asset:
https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
