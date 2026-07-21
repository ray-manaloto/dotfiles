# Magpie Query Tuning

Magpie plans each query into per-partition subplans. The dominant cost is
almost always partition fan-out, not CPU.

If a query is slow, check how many partitions it touched before you touch
any Magpie setting. A query touching archival partitions is slow for storage
reasons, not planner reasons — retuning Magpie will not help.

Shard rebalancing runs nightly and is unrelated to query latency.
