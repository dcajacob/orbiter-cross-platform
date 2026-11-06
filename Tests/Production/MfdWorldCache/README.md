# World-owned MFD caches

The current Windows normal-cleanup regression passed twenty Debug/automatic
worlds, then crashed while opening Map MFD in Debug/SSE2 world seventeen.
Sixteen prior worlds had completed normal cleanup. The retained access-violation
stack enters `VectorMap::SetCBody` from `Instrument_Map` during panel loading.
The matrix failed; Release profiles were not run.

Map preserves the last owner and body pointers in static `saveprm`. After the
world is destroyed, an allocator can reuse the owner address in the next world.
The constructor then mistakes the new vessel for the old owner and restores a
retired planetary-body pointer. Other built-in MFD caches use the same lifetime
pattern. `Instrument::GlobalExit`, after all MFDs are destroyed and before world
reset, now invalidates their world-owned handles. Scalar preferences and normal
same-world restoration remain unchanged. These are internal static methods;
instance layout and the public SDK are unchanged.

`Cache.Test.py --output <new-directory>` compiles the actual Map constructor,
destructor, GlobalExit method and all nine cleanup methods into a controlled
fixture. It deterministically reuses an owner address, rejects a retired body,
checks same-world restoration and checks all handle retirements. It also
requires missing-cleanup and damaged source-allowance controls to fail. The
fixture never dereferences freed storage and earns no simulator qualification.

The source-conservation reader permits only the exact handle assignments at the
existing world boundary, removes them, and compares the complete original MFD
implementation. The full 622-file extraction audit and focused regression pass.
The original failed Windows capture remains local, archive SHA-256
`aacabe229dcbd8b41f40f0e167e684fd12798bcbc74625afb13211339df34ac9`.
A fresh source-bound Windows build and complete eighty-world run are required
before this repair earns runtime qualification. Phase 6 remains incomplete.
