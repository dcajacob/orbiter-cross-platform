# Original-runtime mathematical functions

The `amd/` files are unchanged selective imports from AMD's MIT-licensed
[Windows math implementation](https://github.com/amd/win-libm), pinned at
`6121d02aef0c775947d5dc655d7fc4ccfe2144ab`. Every file contains AMD's copyright
and MIT permission notice. `sources.lock.json` records the original bytes and
source-archive hash. No prebuilt Windows library is included.

The simulation uses double-precision sine, cosine, arcsine and two-argument
arctangent. The native Earth J71G atmosphere also uses the pinned exponential. Linux preparation converts
assembly syntax and private error/type bindings; the original files stay
unchanged. Their operation ordering is retained. The host OpenGL renderer uses
its own math library. This backend is an internal production simulation
dependency, initially qualified on Linux x86-64 with GCC.

The original application's Microsoft runtime remains the Windows adapter.
Frozen application traces and budgets are authoritative. Matching a primitive
corpus alone cannot establish simulation parity.
