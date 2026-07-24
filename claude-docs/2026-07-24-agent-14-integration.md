# Integration decisions

The integration branch preserves each reviewed agent commit as a merge commit. Lockfile
conflicts were resolved by retaining all declared production dependencies and regenerating
from the combined package manifests. The web package combines cockpit scripts with QA and
Replay scripts rather than selecting either branch wholesale.

The root build target now invokes the actual Next.js production build. Live routes and
workers remain deliberately uncomposed because the real AWS resources, sponsor credentials,
and handler wiring are not available in this integration workspace. This preserves the
repository's fail-closed production contract.
