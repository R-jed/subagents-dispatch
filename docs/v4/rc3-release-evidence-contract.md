# V4.0.0 RC3 Release Evidence Contract

RC3 separates runtime package integrity from candidate-specific release evidence.

Runtime package integrity continues to prove the committed plugin runtime bytes covered by the package manifest.

Candidate-specific release evidence MUST bind the exact candidate under review and publication.

Minimum release evidence identity:

- repository identity
- candidate commit SHA
- candidate tree SHA
- runtime package manifest digest
- production Hook definition digest
- authoritative profile contract digest
- Host campaign contract version
- Host campaign result digest
- Final Review artifact identity when review is required
- Final Review verdict and evidence reference

Host campaign results and Final Review receipts may be external artifacts. If committing an evidence artifact would mutate the candidate it proves, the evidence MUST remain outside the candidate and bind the candidate identity explicitly.

Doctor publication readiness MUST consume one authoritative predicate. A candidate cannot be release-ready when overall runtime health is false, mandatory Host evidence is incomplete, candidate identity has drifted, required Final Review is missing or stale, or any required digest does not match the exact release candidate.

No plain `status = PASS`, arbitrary digest-shaped string, or arbitrary evidence reference is sufficient by itself to satisfy a release gate.
