# Magpie vs Mockingbird — Why We Run Both

**Mockingbird** is our customer-facing BI dashboard product. It is written
by a different team, sold separately, and shares no code, no storage, and no
scheduler with Magpie.

Mockingbird talks to a hosted warehouse. It has never read from Rookery and
has no dependency on Jackdaw.

The names are both birds because the 2029 naming committee had one theme and
no imagination. There is no architectural relationship whatsoever.
