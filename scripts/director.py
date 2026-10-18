#!/usr/bin/env python3
"""
director.py - Literary Director and Character Bible Manager for Fiction Translation & Audiobook Production.

Provides:
1. Style Guide (style_guide.json):
   - Genre, narrative point of view, aesthetic register, negative style constraints
     (e.g. banning Ming/Qing vernacular / martial arts storytelling cliches for modern European fiction).
2. Character Bible (characters.json):
   - Characters with demographics, social standing, psychological profile,
   - Precise dialogue voice & rules (self-references, honorifics, sentence rhythm),
   - Audiobook & Voice Acting Profile (pitch, timbre, pacing, emotional demeanor, casting notes).
3. Chunk Directives Injection:
   - Evaluates source chunk text, matches appearing characters,
   - Generates compact Markdown directives for LLM sub-agents.
4. Human-in-the-Loop Reporting:
   - Exports formatted Markdown review sheets for authors/editors.
   - Exports Dramatis Personae for book frontmatter and audiobook scripts.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

DIRECTOR_SCHEMA_VERSION = 1

VALID_GENDERS = ('male', 'female', 'nonbinary', 'unknown', 'other')
VALID_AGE_GROUPS = ('child', 'teen', 'young_adult', 'adult', 'senior', 'ageless')


def _canonical_json(data):
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


def validate_style_guide(data, filepath="style_guide.json"):
    """Validate style_guide.json schema."""
    if not isinstance(data, dict):
        raise ValueError(f"{filepath}: root must be a JSON object")
    
    required_fields = ["version", "genre", "narrative_register", "dialogue_register", "negative_constraints"]
    for f in required_fields:
        if f not in data:
            raise ValueError(f"{filepath}: missing required field '{f}'")
    
    if not isinstance(data["negative_constraints"], list):
        raise ValueError(f"{filepath}: 'negative_constraints' must be a list of strings")
    return True


def validate_characters(data, filepath="characters.json"):
    """Validate characters.json schema."""
    if not isinstance(data, dict):
        raise ValueError(f"{filepath}: root must be a JSON object")
    if "characters" not in data or not isinstance(data["characters"], list):
        raise ValueError(f"{filepath}: missing 'characters' array")
    
    for idx, char in enumerate(data["characters"]):
        for req in ("id", "source_name", "target_name", "voice_and_dialogue"):
            if req not in char:
                raise ValueError(f"{filepath} [char #{idx}]: missing required field '{req}'")
        
        # Validate dialogue structure
        vd = char["voice_and_dialogue"]
        if not isinstance(vd, dict):
            raise ValueError(f"{filepath} [char #{idx}]: 'voice_and_dialogue' must be an object")
        
        # Audiobook profile (optional but recommended)
        if "audiobook_profile" in char and not isinstance(char["audiobook_profile"], dict):
            raise ValueError(f"{filepath} [char #{idx}]: 'audiobook_profile' must be an object")
            
    return True


def load_director_configs(dir_path):
    """Load style_guide.json, characters.json, and glossary.json from directory."""
    path = Path(dir_path)
    style_path = path / "style_guide.json"
    char_path = path / "characters.json"
    glossary_path = path / "glossary.json"
    
    style_data = None
    char_data = None
    glossary_data = None
    
    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            style_data = json.load(f)
            validate_style_guide(style_data, str(style_path))
            
    if char_path.exists():
        with open(char_path, "r", encoding="utf-8") as f:
            char_data = json.load(f)
            validate_characters(char_data, str(char_path))

    if glossary_path.exists():
        with open(glossary_path, "r", encoding="utf-8") as f:
            glossary_data = json.load(f)
            
    return style_data, char_data, glossary_data


def detect_characters_in_text(text, characters_list):
    """Identify which characters appear in the chunk text using exact name and alias matching."""
    matched = []
    for char in characters_list:
        names_to_check = [char["source_name"]] + char.get("aliases", [])
        # Word boundary pattern for English identifiers
        pattern = r'\b(?:' + '|'.join(re.escape(name) for name in names_to_check if name) + r')\b'
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(char)
    return matched


def generate_chunk_directives(dir_path, chunk_file_path):
    """Generate Markdown prompt segment for a specific chunk."""
    style_data, char_data, _ = load_director_configs(dir_path)
    
    directives = []
    
    # 1. Style Guide Directive
    if style_data:
        directives.append("### 【文学总导演·全书文风与叙事基调指令】")
        directives.append(f"- **作品体裁与世界观**：{style_data.get('genre', '文学作品')}")
        directives.append(f"- **叙事笔触**：{style_data.get('narrative_register', '')}")
        directives.append(f"- **对话总原则**：{style_data.get('dialogue_register', '')}")
        
        negs = style_data.get("negative_constraints", [])
        if negs:
            directives.append("- **核心禁忌（必须绝对避免）**：")
            for neg in negs:
                directives.append(f"  * ❌ {neg}")
        directives.append("")
    
    # 2. Characters Directive
    if char_data and Path(chunk_file_path).exists():
        with open(chunk_file_path, "r", encoding="utf-8") as f:
            chunk_text = f.read()
        
        matched_chars = detect_characters_in_text(chunk_text, char_data.get("characters", []))
        if matched_chars:
            directives.append("### 【文学总导演·本章登场人物台词与声线排演指南】")
            directives.append("> ⚠️ **严禁千人一面**！对话是塑造人物的核心，请严格依照人物的年龄、阶层、性格与说话风格翻译台词：\n")
            for c in matched_chars:
                vd = c.get("voice_and_dialogue", {})
                ab = c.get("audiobook_profile", {})
                
                char_title = f"- **角色：{c.get('target_name', c['source_name'])}** ({c['source_name']})"
                traits = []
                if "gender" in c and c["gender"] != "unknown":
                    traits.append(c["gender"])
                if "age_description" in c:
                    traits.append(c["age_description"])
                elif "age_group" in c:
                    traits.append(c["age_group"])
                if "social_status" in c:
                    traits.append(c["social_status"])
                if traits:
                    char_title += f" [身份/特质: {' | '.join(traits)}]"
                directives.append(char_title)
                
                if "personality" in c:
                    directives.append(f"  * **性格底色**：{c['personality']}")
                if "self_reference" in vd:
                    directives.append(f"  * **人称自称**：{vd['self_reference']}")
                if "cadence_and_tone" in vd:
                    directives.append(f"  * **语气节奏**：{vd['cadence_and_tone']}")
                if "vocabulary_style" in vd:
                    directives.append(f"  * **用词特点**：{vd['vocabulary_style']}")
                if ab and "tone" in ab:
                    directives.append(f"  * **声线情绪（有声书导向）**：{ab['tone']}")
                
                rules = vd.get("rules", [])
                if rules:
                    directives.append("  * **台词翻译准则**：")
                    for r in rules:
                        directives.append(f"    · {r}")
                
                examples = vd.get("example_dialogue", [])
                if examples:
                    directives.append("  * **台词对照示例**：")
                    for ex in examples:
                        directives.append(f"    · 原文: {ex.get('en', '')} → 译文: {ex.get('zh', '')}")
                directives.append("")
    
    return "\n".join(directives).strip()


def export_review_markdown(dir_path):
    """Generate a clean, beautiful human-readable review report in Markdown for human-in-the-loop audit."""
    style_data, char_data, glossary_data = load_director_configs(dir_path)
    lines = []
    lines.append("# 文学总导演档案：全书艺术基调、人物谱系、术语统一与有声书台本指南")
    lines.append("*Human-in-the-Loop 审阅稿：用于文本翻译指导、术语一致性控制与后续有声书（Audiobook）录制 Casting*\n")
    lines.append("---\n")
    
    if style_data:
        lines.append("## 一、 全书文风与美学风格设定（Style Guide）\n")
        lines.append(f"- **作品题材**：{style_data.get('genre', '')}")
        lines.append(f"- **叙事视角**：{style_data.get('narrative_point_of_view', '第三人称')}")
        lines.append(f"- **叙述正文文风**：\n  > {style_data.get('narrative_register', '')}\n")
        lines.append(f"- **人物对话总原则**：\n  > {style_data.get('dialogue_register', '')}\n")
        
        negs = style_data.get("negative_constraints", [])
        if negs:
            lines.append("### 🚫 禁忌风格清单（Negative Constraints）")
            for neg in negs:
                lines.append(f"- ❌ {neg}")
            lines.append("")
        
        case_studies = style_data.get("translation_case_studies", [])
        if case_studies:
            lines.append("## 二、 直译与意译界限案例辨析（Translation Calibration & Case Studies）\n")
            lines.append("> ⚠️ **翻译准则**：坚决破除欧化生硬直译与“塑料中文”，依据汉语母语口读耳感（Ear Test）与地道意合逻辑重构，以下为全书标杆案例对照：\n")
            for cs in case_studies:
                lines.append(f"### ⚖️ 【{cs.get('id', '')}】 {cs.get('type', '')}")
                lines.append(f"- 🇬🇧 **英文原文**：*{cs.get('en', '')}*")
                lines.append(f"- ❌ **死板直译（避坑）**：{cs.get('literal_zh', '')}")
                lines.append(f"- ✅ **推荐地道意译**：**{cs.get('idiomatic_zh', '')}**")
                lines.append(f"- 💡 **导演解析与取舍理由**：{cs.get('director_notes', '')}\n")
            lines.append("---\n")

    if glossary_data and "terms" in glossary_data:
        lines.append("## 三、 核心术语与重要概念统一对照表（Glossary Table）\n")
        lines.append("| 英文原词 / Source | 统一规范译名 / Target | 类别 / Category | 别名与形态 / Aliases | 核心说明 / Notes |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for t in glossary_data.get("terms", []):
            aliases_str = ", ".join(t.get("aliases", [])) if t.get("aliases") else "-"
            lines.append(f"| **{t['source']}** | **{t['target']}** | {t.get('category', '-')} | {aliases_str} | {t.get('notes', '-')} |")
        lines.append("\n---\n")
            
    if char_data:
        lines.append("## 四、 核心人物谱系与台词人设表（Character Bible & Voice Casting）\n")
        lines.append("| 人物原名 | 中文标准译名 | 性别/年龄段 | 身份背景 | 有声书声线特征 (Voice Profile) |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in char_data.get("characters", []):
            ab = c.get("audiobook_profile", {})
            age_info = c.get("age_description", c.get("age_group", "未知"))
            vp = ab.get("voice_profile", "未指定")
            lines.append(f"| **{c['source_name']}** | **{c.get('target_name', '-')}** | {c.get('gender', '')} / {age_info} | {c.get('social_status', '-')} | {vp} |")
        lines.append("\n---\n")
        
        lines.append("### 详细角色台词规范与有声配音小传\n")
        for c in char_data.get("characters", []):
            lines.append(f"### 🎭 【{c.get('target_name', c['source_name'])}】 (*{c['source_name']}*)")
            if c.get("aliases"):
                lines.append(f"- **原著别称/头衔**：{', '.join(c['aliases'])}")
            lines.append(f"- **性格深度剖析**：{c.get('personality', '无')}")
            
            vd = c.get("voice_and_dialogue", {})
            lines.append(f"- **台词语言习惯**：")
            lines.append(f"  - **自称方式**：{vd.get('self_reference', '我')}")
            lines.append(f"  - **语速与节奏**：{vd.get('cadence_and_tone', '自然')}")
            lines.append(f"  - **词汇风格**：{vd.get('vocabulary_style', '标准现代文学白话')}")
            
            rules = vd.get("rules", [])
            if rules:
                lines.append("  - **翻译执行规则**：")
                for r in rules:
                    lines.append(f"    * {r}")
                    
            examples = vd.get("example_dialogue", [])
            if examples:
                lines.append("  - **标杆台词示范**：")
                for ex in examples:
                    lines.append(f"    * 🇬🇧 原文: *{ex.get('en', '')}*")
                    lines.append(f"    * 🇨🇳 译文: **{ex.get('zh', '')}**")
            
            ab = c.get("audiobook_profile", {})
            if ab:
                lines.append(f"- **🎧 有声书录制指南 (Audiobook Director Notes)**：")
                lines.append(f"  - **声线类型**：{ab.get('voice_profile', '标准旁白')}")
                lines.append(f"  - **音高与质感**：{ab.get('pitch_and_texture', '适中')}")
                lines.append(f"  - **演播情绪基调**：{ab.get('tone', '平稳')}")
                lines.append(f"  - **配音重点提示**：{ab.get('casting_notes', '无特别交代')}")
            lines.append("")
            
    return "\n".join(lines)


def export_dramatis_personae(dir_path):
    """Export Dramatis Personae (Actors list) for book frontmatter."""
    _, char_data, _ = load_director_configs(dir_path)
    if not char_data:
        return ""
    
    lines = ["## 出场人物志 (Dramatis Personae)\n"]
    for c in char_data.get("characters", []):
        name = f"**{c.get('target_name', c['source_name'])}**（*{c['source_name']}*）"
        desc = c.get("age_description", "")
        if c.get("social_status"):
            desc = f"{c['social_status']}，{desc}" if desc else c['social_status']
        if c.get("personality"):
            desc += f"。{c['personality']}。"
        lines.append(f"- {name}：{desc}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Literary Director CLI for Fiction Translation & Audiobooks")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # print-directives-for-chunk
    p_chunk = subparsers.add_parser("print-directives-for-chunk", help="Print prompt directives for a specific chunk")
    p_chunk.add_argument("dir_path", help="Path containing style_guide.json and characters.json")
    p_chunk.add_argument("chunk_path", help="Path to chunk markdown file")
    
    # export-review
    p_review = subparsers.add_parser("export-review", help="Export Markdown review report for humans")
    p_review.add_argument("dir_path", help="Path containing style_guide.json and characters.json")
    p_review.add_argument("-o", "--output", help="Output file path (default: stdout)")
    
    # export-dramatis-personae
    p_dp = subparsers.add_parser("export-dramatis-personae", help="Export Dramatis Personae for book frontmatter")
    p_dp.add_argument("dir_path", help="Path containing characters.json")
    p_dp.add_argument("-o", "--output", help="Output file path (default: stdout)")
    
    # check
    p_check = subparsers.add_parser("check", help="Validate style_guide.json and characters.json")
    p_check.add_argument("dir_path", help="Directory to validate")
    
    args = parser.parse_args()
    
    if args.command == "check":
        style, chars, glossary = load_director_configs(args.dir_path)
        gloss_count = len(glossary.get('terms', [])) if glossary and 'terms' in glossary else 0
        print(f"Validation successful. Style guide: {'Loaded' if style else 'Missing'}, Characters: {len(chars['characters']) if chars else 0} loaded, Glossary: {gloss_count} terms loaded.")
    elif args.command == "print-directives-for-chunk":
        directives = generate_chunk_directives(args.dir_path, args.chunk_path)
        if directives:
            print(directives)
    elif args.command == "export-review":
        content = export_review_markdown(args.dir_path)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Review exported to {args.output}")
        else:
            print(content)
    elif args.command == "export-dramatis-personae":
        content = export_dramatis_personae(args.dir_path)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Dramatis Personae exported to {args.output}")
        else:
            print(content)


if __name__ == "__main__":
    main()
