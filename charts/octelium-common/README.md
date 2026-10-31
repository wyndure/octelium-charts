# Octelium common library

Shared Helm helpers for component labels, image references, environment overrides, SPIFFE mounting and resource-server discovery. Application charts bundle this library as a local dependency.

Update its chart version and the application dependency versions together when releasing changes. `make package` creates self-contained chart archives with matching dependency versions.

GNU AGPL v3; see [LICENSE](LICENSE).
