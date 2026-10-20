# A Journal Day ends at 04:00 local time, not midnight

People who journal at night routinely write after midnight about the day that just ended. Under a midnight boundary those entries land on the following date, which splits one night's reflection across two days, double-counts days, and breaks streaks for exactly the users the app is designed around. A Journal Day therefore runs from `DAY_BOUNDARY_HOUR` (default 04:00) to the same hour the next morning.

## Consequences

`created_at` is stored in UTC, but grouping, streaks, and sidebar date headers are computed in the Author's local time against the boundary hour — so the journal day of an Entry is derived, never stored. Changing `DAY_BOUNDARY_HOUR` retroactively re-buckets existing Entries and can therefore change a reported streak.
