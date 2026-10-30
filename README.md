# devops-dockerfile-base-image-pins

Check that every `FROM` line in your Dockerfiles points at a base image you can
reproduce: a specific tag, and ideally a digest. Stdlib Python, no daemon and no
network needed.

## What it flags

| Rule | Meaning |
| --- | --- |
| `untagged` | `FROM alpine` resolves to `latest` |
| `latest-tag` | `FROM alpine:latest` |
| `no-digest` | tagged, but not pinned with `@sha256:...` (warning) |
| `unresolved-arg` | `FROM ${BASE}` where the `ARG` has no default |

`FROM scratch` and references to an earlier build stage (`FROM build`) are
skipped. `ARG` defaults declared before the first `FROM` are expanded.

## Usage

```sh
python3 pinaudit.py Dockerfile
python3 pinaudit.py --strict path/to/*.Dockerfile   # warnings fail too
```

Exit code is 1 when an error is found (or a warning with `--strict`).
