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

## Example

Output for `examples/loose.Dockerfile`:

```text
examples/loose.Dockerfile:2: error: [untagged] node has no tag and resolves to latest
examples/loose.Dockerfile:3: error: [latest-tag] alpine:latest uses the latest tag
examples/loose.Dockerfile:4: error: [unresolved-arg] ${BASE} uses an ARG with no default; set one before the first FROM
examples/loose.Dockerfile:5: warning: [no-digest] registry.local:5000/team/app:1.4 is tagged but not pinned by digest
```

## Validate

```sh
make validate
```

Runs the unit tests, requires `examples/pinned.Dockerfile` to pass with
`--strict`, and requires `examples/loose.Dockerfile` to fail. CI runs the same
target. Digests in the examples are placeholders, not real images.

## Limits

The audit is text-based. It does not resolve a tag to a digest or check that a
digest exists in a registry, and it ignores `FROM` lines in files other than the
ones you pass in. Per-stage `ARG` values passed with `--build-arg` are not seen.
