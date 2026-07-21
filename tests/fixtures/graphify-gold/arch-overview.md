# Corvid Platform — Architecture Overview

Corvid is our internal analytics platform. It has three services.

**Rookery** is the storage layer. It keeps recent partitions on NVMe and
spills older partitions to object storage once they age out.

**Magpie** is the query engine. It plans a query, fans the plan out across
Rookery partitions, and merges the partial results.

**Jackdaw** is the scheduler. It decides when Magpie runs a materialization
job and how many workers each job gets.

Jackdaw submits work to Magpie. Magpie reads from Rookery. Nothing writes
to Rookery except the ingest daemon.

Do not confuse Rookery with **Rookwood**, the deprecated 2029 prototype.
Rookwood shares no code with Rookery and is not deployed anywhere.
