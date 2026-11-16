# Automatic FBM coverage: diagnosis and acceptance criteria

Issue: #56. Branch isolated from main. No runtime behavior changed yet.

## Verified in code

- `competition_auto_sync.py`: one group every five minutes, one player batch of up to five every 30 minutes.
- The player cursor traverses teams and groups and then applies `PLAYER_CYCLE_DELAY = 24h`, irrespective of remaining incomplete snapshots.
- A failed partial batch is retried once; subsequent failure advances the cursor.
- `competition_player_stats.py` skips snapshots deemed complete based on roster appearances and valid per-match points.
- `competition_coverage.py` counts pending players with appearances but without a sufficiently complete archived snapshot; this can include source data not yet published.

## Required changes before beta

1. Preserve five-player rate limit and persist resumable cursor.
2. On cycle completion, distinguish genuine retryable pending from unavailable official data; use bounded backoff, not an unconditional busy loop.
3. Ensure no competition starves when another has incomplete records.
4. Expose useful aggregate status without exposing player identities.
5. Do not claim 100% when official match stats are unavailable; count those separately.
6. Unit tests: restart, no-data, transient error, repeat incomplete, newly added player, cross-group fairness and unchanged-cache skip.
7. Validate CI and Home Assistant DEV before release.

## Baseline 2026-11-15

HA `sensor.competiciones`: 186/327 complete; 141 pending. Halcones Arroyofresno Grupo 17: 22/62 complete, 40 pending. Auto-refresh reports OK; standings and fixtures are current.
