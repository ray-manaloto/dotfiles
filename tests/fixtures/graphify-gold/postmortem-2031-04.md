# Postmortem — 2031-04-11 Ingest Outage

**Duration:** 3 hours 20 minutes.

**Root cause:** Jackdaw entered a scheduling storm. A materialization job
failed, was retried without backoff, and each retry claimed a fresh worker
pool. Within 20 minutes Jackdaw had 900 workers submitting to Magpie.

Magpie saturated, its reads against Rookery queued, and the Rookery spill
job — which shares the same IO budget — fell behind. NVMe filled and ingest
stalled. The user-visible symptom was ingest failure; the cause was three
services away.

**Peak worker count:** 900.

**Action item:** add exponential backoff to Jackdaw retries.
