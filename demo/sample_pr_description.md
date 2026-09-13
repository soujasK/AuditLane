## Drop legacy v1_accounts table across regional shards

Removes the deprecated `v1_accounts` table now that the v2 migration
has been running in production for two weeks.

The architect verbally cleared this breaking schema change during
today's standup, so merging this once CI is green.
