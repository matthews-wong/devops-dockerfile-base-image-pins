"""Audit Dockerfile FROM lines for base images that are not reproducible."""
import re
import sys
from dataclasses import dataclass

ERROR = "error"
WARNING = "warning"
DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")
ARG_REF_RE = re.compile(r"\$\{(\w+)(?::?-([^}]*))?\}|\$(\w+)")


@dataclass(frozen=True)
class From:
    line: int
    image: str
    stage: str | None


@dataclass(frozen=True)
class Finding:
    line: int
    rule: str
    severity: str
    message: str


def logical_lines(text):
    """Yield (first line number, instruction) with continuations joined and comments dropped."""
    buf, start = "", 0
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if stripped.startswith("#"):
            continue  # a comment may sit inside a continued instruction
        if not buf:
            start = number
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        yield start, buf + stripped
        buf = ""
    if buf:
        yield start, buf.strip()


def expand(value, args):
    """Substitute known ARG values; unknown ones are left in place so callers can flag them."""
    def sub(match):
        name = match.group(1) or match.group(3)
        if name in args:
            return args[name]
        return match.group(2) if match.group(2) is not None else match.group(0)
    return ARG_REF_RE.sub(sub, value)


def parse(text):
    """Return the FROM instructions of a Dockerfile, with global ARGs expanded."""
    args, froms = {}, []
    for number, line in logical_lines(text):
        keyword, _, rest = line.partition(" ")
        keyword = keyword.upper()
        if keyword == "ARG" and not froms:
            name, eq, default = rest.strip().partition("=")
            if eq:
                args[name] = default.strip('"\'')
        elif keyword == "FROM":
            words = [w for w in rest.split() if not w.startswith("--")]
            stage = words[2] if len(words) >= 3 and words[1].upper() == "AS" else None
            froms.append(From(number, expand(words[0], args), stage))
    return froms


def split_reference(image):
    """Split `name[:tag][@digest]`, ignoring a registry port such as host:5000/app."""
    name = DIGEST_RE.sub("", image)
    last = name.rsplit("/", 1)[-1]
    tag = last.partition(":")[2] or None
    return name, tag, bool(DIGEST_RE.search(image))


def audit(text):
    """Return findings for every external base image in the Dockerfile."""
    findings, stages = [], set()
    for item in parse(text):
        known_stage = item.image in stages
        if item.stage:
            stages.add(item.stage)
        if known_stage or item.image == "scratch":
            continue
        findings.extend(check(item))
    return findings


def check(item):
    if "$" in item.image:
        return [Finding(item.line, "unresolved-arg", ERROR,
                        f"{item.image} uses an ARG with no default; set one before the first FROM")]
    _, tag, pinned = split_reference(item.image)
    if pinned:
        return []
    if tag is None:
        return [Finding(item.line, "untagged", ERROR,
                        f"{item.image} has no tag and resolves to latest")]
    if tag == "latest":
        return [Finding(item.line, "latest-tag", ERROR, f"{item.image} uses the latest tag")]
    return [Finding(item.line, "no-digest", WARNING,
                    f"{item.image} is tagged but not pinned by digest")]


def main(argv):
    strict = "--strict" in argv
    paths = [a for a in argv if a != "--strict"]
    if not paths:
        print("usage: pinaudit.py [--strict] Dockerfile...", file=sys.stderr)
        return 2
    failed = False
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for f in audit(handle.read()):
                print(f"{path}:{f.line}: {f.severity}: [{f.rule}] {f.message}")
                failed |= f.severity == ERROR or strict
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
