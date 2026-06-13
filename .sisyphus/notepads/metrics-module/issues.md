# Issues — metrics-module

_No issues yet._

## __init__.py __all__ count mismatch (14 vs 13)
- Task EXPECTED OUTCOME + 4b verify assert `len(__all__) == 13`
- But task 4a "Content to create" AND design doc lines 777-790 BOTH list 14 names
- Actual count: 1 config + 8 models + 5 core components = 14
- All 14 are legitimate public API (MetricsHealth analogous to CacheHealth/HttpHealth which ARE exported)
- Decision: kept 14 to match authoritative design doc. The "13" in criteria is a miscount.
- generate_exposition correctly NOT in __all__ (per learnings + task MUST NOT)
