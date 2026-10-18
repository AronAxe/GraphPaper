"""Static skill packaging checks; not a substitute for a live-agent evaluation."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT/'skills/graphpaper'


class SkillFormatTests(unittest.TestCase):
    def test_frontmatter_and_progressive_disclosure(self):
        text=(SKILL/'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\n'))
        header,body=text[4:].split('\n---\n',1)
        values=dict(line.split(': ',1) for line in header.splitlines())
        self.assertEqual(values['name'],SKILL.name)
        self.assertTrue(values['description'].startswith('Use when'))
        self.assertLessEqual(len(values['description']),1024)
        self.assertLess(len(body.split()),650)
        self.assertLess(len(text.splitlines()),500)

    def test_referenced_files_are_included(self):
        for page in SKILL.rglob('*.md'):
            for target in re.findall(r'\[[^]]*\]\(([^)]+)\)',page.read_text(encoding='utf-8')):
                if '://' not in target and not target.startswith('#'):
                    with self.subTest(page=page.name,target=target):
                        self.assertTrue((page.parent/target.split('#')[0]).is_file())

    def test_all_requested_workflows_are_present(self):
        files={p.name for p in (SKILL/'references').glob('*.md')}
        self.assertTrue({'setup.md','api.md','writing.md','science.md','voice-and-editing.md','evaluation.md'}<=files)
        body=(SKILL/'SKILL.md').read_text(encoding='utf-8')
        for important in ['System One','once','409','unscored','Current instructions','provider consent']:
            self.assertIn(important,body)

    def test_example_database_ids_match_contract(self):
        text=(SKILL/'references/science.md').read_text(encoding='utf-8')
        for name in ['pubmed','semantic_scholar','arxiv','crossref','europe_pmc']:
            self.assertIn('`'+name+'`',text)
        self.assertIn('Do not POST `/research/confirm`',text)


if __name__=='__main__': unittest.main()
