"""The fixed Phase 6 software, operator, and physical-controller acceptance checklist."""
from contracts import COHORTS, PROFILES, case_ids, load, ROOT, require

WORKFLOWS = ('dg-orbit', 'virtual-cockpit-dg', 'virtual-cockpit-demo', 'dgs-takeoff',
             'iss-docking-dg', 'iss-docking-demo', 'atmospheric-autopilot',
             'moon-stock-playback', 'moon-brake-continuation', 'atlantis-resupply',
             'atlantis-rms-payload', 'atlantis-ascent')
FAMILIES = ('Atlantis', 'Atlantis_SRB', 'Atlantis_Tank', 'Carina', 'Leonardo_mplm',
            'Module2', 'Dragonfly', 'HST', 'LDEF', 'SolarSail', 'Quadcopter')
CLASS_FACETS = ('source-abi', 'capabilities', 'interactions', 'persistence',
                'resource-ownership', 'twenty-cycle-teardown', 'rejection-controls')


def requirements():
    locked = load(ROOT / 'Tests/Production/production-source.lock.json')
    require(locked['scenario_count'] == len(locked['scenarios']) == 157, 'Complete locked 157-entry inventory required')
    stock = [scene['path'] for scene in locked['scenarios']]
    cases = case_ids()
    return {
        'runner-controls': dict(depends_on=[], required=['full-versus-selected','terminal-statuses',
            'cancellation','process-receipts','completed-capture-reuse','declared-share-roots',
            'disk-preflight','archive-restoration'], final_candidate_required=False),
        'numerical-reload': dict(depends_on=['runner-controls'], profiles=list(PROFILES),
            cohorts=list(COHORTS), cases=['remaining_stock_003'], phases=['stock-writer','windows-save-reload'],
            repeats=2, required=['first-differing-operation','observer-on-off-equivalence',
                'actual-crt-providers','failing-and-neighbour-input-regression','all-existing-budgets'], final_candidate_required=False),
        'general-api': dict(depends_on=['runner-controls'], profiles=list(PROFILES),
            cohorts=['current-windows','native'], required=['original-bytes-and-failure-preserved',
                'locked-spice-oracle','symmetric-comparator','nil-false-and-wrong-value-controls'], final_candidate_required=False),
        'class-eligibility': dict(depends_on=['numerical-reload','general-api'], profiles=list(PROFILES),
            families=list(FAMILIES), required=list(CLASS_FACETS), final_candidate_required=False),
        'candidate-freeze': dict(depends_on=['class-eligibility'], required=['windows-debug-release',
            'four-native-profiles','application-observer-runner-reference-identities',
            'dependency-and-provider-inventories','discovered-unit-test-inventory']),
        'remaining-stock': dict(depends_on=['candidate-freeze'], profiles=list(PROFILES),
            cohorts=list(COHORTS), cases=list(cases), phases=['stock-writer','windows-save-reload'], repeats=2,
            runs_per_cohort=608, required=['complete-state','clocks','cameras','complete-saved-content',
                'full-frames','exact-same-windows-save','fresh-launch-worker-desktop-process-receipts']),
        'normal-admission': dict(depends_on=['candidate-freeze'], profiles=list(PROFILES),
            cohorts=['native'], entry_points=stock, runs=628,
            required=['normal-host','no-class-rejections','versioned-general-api-correction',
                      'unchanged-intentional-exit-policy']),
        'named-workflows': dict(depends_on=['candidate-freeze'], profiles=list(PROFILES),
            cohorts=['current-windows','native'], workflows=list(WORKFLOWS), repeats=2,
            required=['complete-original-vessel-roster','tick-indexed-original-input-dispatch',
                'no-state-placement-setters','actual-save-and-F5','moon-stock-parity-and-distinct-landed-braking']),
        'core-interfaces': dict(depends_on=['candidate-freeze'], profiles=list(PROFILES),
            required=['all-discovered-unit-tests-with-actual-totals','three-hud-modes','ten-stock-mfds',
                'gdi-sketchpad','dialogs','lua-aap','recording-playback','invalid-input-and-module-controls',
                'terminal-hud-mfd-text-and-images-without-new-masks']),
        'lifecycle-input': dict(depends_on=['candidate-freeze'], profiles=list(PROFILES), cycles=20,
            backends=['x11','wayland'], scales=[1,2], views=['panel','virtual-cockpit'],
            required=['load-reload-unload','paused-attachments','lua-ownership','actual-provider-matrices',
                'clean-exits','unsuppressed-native-sanitizers']),
        'performance': dict(depends_on=['remaining-stock','normal-admission','named-workflows',
                                      'core-interfaces','lifecycle-input'],
            profile='Release-automatic', resolution=[1920,1080], quality='medium', device='Intel',
            backends=['wayland','xwayland'], scenes=3, repeats=2, runs=12,
            median_ms_max=33, p95_ms_max=50,
            required=['serial','ac-power','no-competing-qualification-jobs']),
        'hands-on': dict(depends_on=['performance'], required=['physical-keyboard-mouse',
            'cockpit-view-changes','controls','typing-cancellation','focus-recovery','save-F5-reload','normal-exit']),
        'archive-audit': dict(depends_on=['hands-on'], required=['independent-final-evidence-reread',
            'every-required-case-profile-repetition','versioned-sealed-local-archives',
            'archive-restoration','central-status-and-supported-class-documents']),
        'controller': dict(depends_on=['hands-on'], required=['real-axes-buttons','deadzones',
            'throttle-arming','keyboard-handoff','disconnect-reconnect','physical-hardware']),
    }
