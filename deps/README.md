# Parent systems (vendored by install)

This directory is filled by **`scripts/install.ps1`** / **`scripts/install.sh`**:

| Path | Upstream (your forks) |
|------|------------------------|
| `deps/buzz` | https://github.com/Questing-VR/buzz |
| `deps/zeroclaw` | https://github.com/Questing-VR/zeroclaw |
| `deps/openAGI` | https://github.com/Questing-VR/openAGI |

They are **not** copied into git history (large monorepos). One clone of **BuzzClawAGI** + one install command pulls all three.

After install you also get:

- `deps/path.ps1` / `deps/path.sh` — PATH and env for start scripts
- Built binaries under `deps/*/target/release` when Rust builds succeed
