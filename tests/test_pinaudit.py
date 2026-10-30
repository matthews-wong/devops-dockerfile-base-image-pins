import unittest

import pinaudit

DIGEST = "@sha256:" + "a" * 64


def rules(text):
    return [(f.line, f.rule) for f in pinaudit.audit(text)]


class ParseTests(unittest.TestCase):
    def test_continuation_and_comment_inside_instruction(self):
        text = "FROM \\\n# note\n  alpine:3.20 AS base\n"
        self.assertEqual(pinaudit.parse(text), [pinaudit.From(1, "alpine:3.20", "base")])

    def test_platform_flag_is_ignored(self):
        froms = pinaudit.parse("FROM --platform=$BUILDPLATFORM alpine:3.20")
        self.assertEqual(froms[0].image, "alpine:3.20")

    def test_arg_default_is_expanded(self):
        froms = pinaudit.parse("ARG V=3.20\nFROM alpine:${V}")
        self.assertEqual(froms[0].image, "alpine:3.20")

    def test_arg_after_from_is_not_global(self):
        froms = pinaudit.parse("FROM alpine:3.20\nARG V=1\nFROM busybox:${V}")
        self.assertEqual(froms[1].image, "busybox:${V}")


class AuditTests(unittest.TestCase):
    def test_untagged(self):
        self.assertEqual(rules("FROM node"), [(1, "untagged")])

    def test_latest(self):
        self.assertEqual(rules("FROM node:latest"), [(1, "latest-tag")])

    def test_tag_without_digest_is_a_warning(self):
        (finding,) = pinaudit.audit("FROM node:22")
        self.assertEqual((finding.rule, finding.severity), ("no-digest", pinaudit.WARNING))

    def test_digest_pinned_passes(self):
        self.assertEqual(rules(f"FROM node:22{DIGEST}"), [])
        self.assertEqual(rules(f"FROM node{DIGEST}"), [])

    def test_registry_port_is_not_a_tag(self):
        self.assertEqual(rules("FROM localhost:5000/app"), [(1, "untagged")])

    def test_scratch_and_stage_references_are_skipped(self):
        text = f"FROM node:22{DIGEST} AS build\nFROM build AS test\nFROM scratch\n"
        self.assertEqual(rules(text), [])

    def test_unresolved_arg(self):
        self.assertEqual(rules("ARG BASE\nFROM ${BASE}"), [(2, "unresolved-arg")])

    def test_arg_default_syntax_in_from(self):
        self.assertEqual(rules("FROM ${BASE:-alpine}"), [(1, "untagged")])


if __name__ == "__main__":
    unittest.main()
