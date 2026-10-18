#!/usr/bin/env python3
"""Unit tests for director.py - Literary Director and Character Bible CLI."""

import json
import os
import shutil
import tempfile
import unittest

from scripts import director


class DirectorValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_validate_style_guide_success(self):
        valid = {
            "version": 1,
            "genre": "Fiction",
            "narrative_register": "Modern Chinese",
            "dialogue_register": "Natural speech",
            "negative_constraints": ["No archaic words"]
        }
        self.assertTrue(director.validate_style_guide(valid))

    def test_validate_style_guide_missing_field(self):
        invalid = {"version": 1, "genre": "Fiction"}
        with self.assertRaises(ValueError):
            director.validate_style_guide(invalid)

    def test_validate_characters_success(self):
        valid = {
            "version": 1,
            "characters": [
                {
                    "id": "hero",
                    "source_name": "Hero",
                    "target_name": "英雄",
                    "voice_and_dialogue": {
                        "self_reference": "我",
                        "rules": ["Speak boldly"]
                    },
                    "audiobook_profile": {
                        "voice_profile": "Deep baritone"
                    }
                }
            ]
        }
        self.assertTrue(director.validate_characters(valid))

    def test_detect_characters_and_chunk_directives(self):
        style = {
            "version": 1,
            "genre": "Sci-Fi",
            "narrative_register": "Nordic minimalist",
            "dialogue_register": "Clinical statements",
            "negative_constraints": ["No slang"]
        }
        chars = {
            "version": 1,
            "characters": [
                {
                    "id": "c1",
                    "source_name": "Cadet 04",
                    "target_name": "四号学员",
                    "aliases": ["Cadet", "04"],
                    "personality": "Quiet and devoted",
                    "voice_and_dialogue": {
                        "self_reference": "我",
                        "cadence_and_tone": "Hesitant",
                        "rules": ["Never shout"]
                    },
                    "audiobook_profile": {
                        "tone": "Subdued",
                        "voice_profile": "Soft tenor"
                    }
                }
            ]
        }
        with open(os.path.join(self.tmp, "style_guide.json"), "w", encoding="utf-8") as f:
            json.dump(style, f)
        with open(os.path.join(self.tmp, "characters.json"), "w", encoding="utf-8") as f:
            json.dump(chars, f)

        chunk_path = os.path.join(self.tmp, "chunk0001.md")
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write("Yesterday Cadet 04 entered the cleaning room.")

        directives = director.generate_chunk_directives(self.tmp, chunk_path)
        self.assertIn("【文学总导演·全书文风与叙事基调指令】", directives)
        self.assertIn("【文学总导演·本章登场人物台词与声线排演指南】", directives)
        self.assertIn("四号学员", directives)
        self.assertIn("Cadet 04", directives)

    def test_export_review_and_dramatis_personae(self):
        style = {
            "version": 1,
            "genre": "Epic",
            "narrative_register": "Grand",
            "dialogue_register": "Elevated",
            "negative_constraints": ["No cliches"],
            "translation_case_studies": [
                {
                    "id": "case_1",
                    "type": "Metaphor",
                    "en": "Cold as ice",
                    "literal_zh": "冷如冰",
                    "idiomatic_zh": "冷若冰霜",
                    "director_notes": "Use natural Chinese phrasing"
                }
            ]
        }
        chars = {
            "version": 1,
            "characters": [
                {
                    "id": "king",
                    "source_name": "King Arthur",
                    "target_name": "亚瑟王",
                    "social_status": "Monarch",
                    "voice_and_dialogue": {"self_reference": "我"}
                }
            ]
        }
        glossary = {
            "version": 2,
            "terms": [
                {"source": "Camelot", "target": "卡美洛", "category": "place"}
            ]
        }
        with open(os.path.join(self.tmp, "style_guide.json"), "w", encoding="utf-8") as f:
            json.dump(style, f)
        with open(os.path.join(self.tmp, "characters.json"), "w", encoding="utf-8") as f:
            json.dump(chars, f)
        with open(os.path.join(self.tmp, "glossary.json"), "w", encoding="utf-8") as f:
            json.dump(glossary, f)

        review_md = director.export_review_markdown(self.tmp)
        self.assertIn("文学总导演档案", review_md)
        self.assertIn("直译与意译界限案例辨析", review_md)
        self.assertIn("核心术语与重要概念统一对照表", review_md)
        self.assertIn("卡美洛", review_md)
        self.assertIn("亚瑟王", review_md)

        dp_md = director.export_dramatis_personae(self.tmp)
        self.assertIn("出场人物志 (Dramatis Personae)", dp_md)
        self.assertIn("亚瑟王", dp_md)


if __name__ == "__main__":
    unittest.main()
