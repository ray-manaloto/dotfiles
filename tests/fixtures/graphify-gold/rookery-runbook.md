# Rookery Runbook

Rookery holds partitions in two places. Hot partitions live on local NVMe.
Once a partition has not been read for 14 days it is moved to the cold tier,
which is backed by S3.

Reading from the cold tier costs roughly 40x the latency of NVMe. A query
that touches cold-tier partitions will look pathologically slow even though
Rookery is healthy.

If the spill job falls behind, NVMe fills and ingest stalls. Check the spill
queue depth first. The 14-day threshold is configurable but has not been
changed since 2030.
