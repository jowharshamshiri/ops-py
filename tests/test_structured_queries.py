"""Tests for structured_queries.py — mirrors Rust structured_queries.rs tests TEST024-TEST028."""

import pytest

from ops.structured_queries import (
    OutlineEntry,
    FlatOutlineEntry,
    ListingOutline,
    OutlineMetadata,
    generate_outline_schema,
)


# TEST024: Build a flat ListingOutline with depth-0 entries and verify max_depth, levels, and flatten count
def test_024_simple_flat_outline():
    outline = ListingOutline()
    outline.entries = [
        OutlineEntry(title="Introduction", level=0, page="1"),
        OutlineEntry(title="Chapter 1: Getting Started", level=0, page="5"),
        OutlineEntry(title="Chapter 2: Advanced Topics", level=0, page="15"),
        OutlineEntry(title="Conclusion", level=0, page="25"),
    ]

    assert outline.max_depth() == 0
    assert len(outline.entries_at_level(0)) == 4
    assert len(outline.flatten()) == 4


# TEST025: Build a two-level outline with chapters and sections and verify depth, level counts, and flatten
def test_025_hierarchical_outline():
    outline = ListingOutline()

    chapter1 = OutlineEntry(title="Chapter 1: Basics", level=0, page="10", entry_type="chapter")
    chapter1.add_child(OutlineEntry(title="1.1 Introduction", level=1, page="10"))
    chapter1.add_child(OutlineEntry(title="1.2 Fundamentals", level=1, page="15"))

    chapter2 = OutlineEntry(title="Chapter 2: Advanced", level=0, page="20", entry_type="chapter")
    chapter2.add_child(OutlineEntry(title="2.1 Complex Topics", level=1, page="20"))

    outline.entries = [chapter1, chapter2]

    assert outline.max_depth() == 1
    assert len(outline.entries_at_level(0)) == 2
    assert len(outline.entries_at_level(1)) == 3
    assert len(outline.flatten()) == 5  # 2 chapters + 3 sections


# TEST026: Build a three-level part/chapter/section outline and verify depth and per-level entry counts
def test_026_complex_part_based_outline():
    outline = ListingOutline()

    # Part I with chapters
    part1 = OutlineEntry(title="Part I: Foundations", level=0, page="1", entry_type="part")

    chapter1 = OutlineEntry(title="Chapter 1: Introduction", level=1, page="3", entry_type="chapter")
    chapter1.add_child(OutlineEntry(title="1.1 Overview", level=2, page="3"))
    chapter1.add_child(OutlineEntry(title="1.2 Scope", level=2, page="5"))

    chapter2 = OutlineEntry(title="Chapter 2: Background", level=1, page="8", entry_type="chapter")

    part1.add_child(chapter1)
    part1.add_child(chapter2)

    # Part II
    part2 = OutlineEntry(title="Part II: Applications", level=0, page="15", entry_type="part")

    outline.entries = [part1, part2]

    assert outline.max_depth() == 2
    assert len(outline.entries_at_level(0)) == 2  # 2 parts
    assert len(outline.entries_at_level(1)) == 2  # 2 chapters
    assert len(outline.entries_at_level(2)) == 2  # 2 sections
    assert len(outline.flatten()) == 6  # 2 parts + 2 chapters + 2 sections


# TEST027: Flatten a nested outline and verify each entry's path reflects its ancestry correctly
def test_027_flatten_preserves_hierarchy():
    outline = ListingOutline()

    part = OutlineEntry(title="Part I", level=0, page="1")
    chapter = OutlineEntry(title="Chapter 1", level=1, page="3")
    chapter.add_child(OutlineEntry(title="Section 1.1", level=2, page="3"))
    part.add_child(chapter)
    outline.entries = [part]

    flat = outline.flatten()
    assert len(flat) == 3

    # Check paths
    assert flat[0].path == ["Part I"]
    assert flat[1].path == ["Part I", "Chapter 1"]
    assert flat[2].path == ["Part I", "Chapter 1", "Section 1.1"]


# TEST028: Call generate_outline_schema and verify the returned JSON contains all required definitions
def test_028_schema_generation():
    schema = generate_outline_schema()
    assert isinstance(schema, dict)
    assert isinstance(schema["properties"]["entries"], dict)
    assert isinstance(schema["definitions"]["OutlineEntry"], dict)
    assert isinstance(schema["definitions"]["OutlineMetadata"], dict)
