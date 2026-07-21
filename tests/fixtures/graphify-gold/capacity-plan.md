# Capacity Plan — FY32

Jackdaw is provisioned for a hard ceiling of 250 concurrent workers. This
ceiling has been enforced since the scheduler was deployed in 2030 and has
never been exceeded in production.

Magpie is sized to absorb the full 250-worker submission rate with headroom.
Rookery spill throughput is sized against the same number.

No change to the Jackdaw worker ceiling is planned for FY32.
