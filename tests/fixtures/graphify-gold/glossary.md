# Glossary

**Frost storage** — the archival storage class in Corvid. A partition enters
frost storage after an inactivity window and is served from object storage
rather than local disk. Reads are substantially slower.

Note: internal documents written before the 2030 rename use the older term
for this same concept. The two names refer to one mechanism, not two.

**Materialization job** — a scheduled recomputation of a derived table.

**Partition** — the unit of storage and of query fan-out.
