"""Published guides align with the app; explicitly versioned captures retain provenance."""
import hashlib,json,re,unittest
from pathlib import Path
from graphpaper import __version__
from scripts.docs_tool import configuration,render
ROOT=Path(__file__).resolve().parents[2]
class CurrentDocumentationTests(unittest.TestCase):
    def test_wiki_version_matches_application(self):
        self.assertEqual(configuration(ROOT)['docs_version'],__version__)
    def test_core_guides_are_published(self):
        paths={p['source'] for p in configuration(ROOT)['pages']}
        self.assertTrue({'docs/GRAPH-STUDIO.md','docs/VOICE-GRAPHS.md','docs/SYSTEM-ONE.md'}<=paths)
    def test_sidebar_sections_are_contiguous(self):
        sections=[p['section'] for p in configuration(ROOT)['pages']]
        runs=[s for i,s in enumerate(sections) if i==0 or s!=sections[i-1]]
        self.assertEqual(len(runs),len(set(runs)))
    def test_explicitly_versioned_readme_captures_keep_real_provenance(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        images=re.findall(r'!\[[^\]]*\]\(docs/images/([^)]*\.webp)\)',readme)
        self.assertGreaterEqual(len(images),3)
        for name in images:
            match=re.search(r'-v(\d+\.\d+)\.webp$',name)
            self.assertIsNotNone(match,'Application screenshots must state their capture version')
            version=match.group(1)
            manifest=json.loads((ROOT/f'docs/images/screenshots-v{version}.json').read_text())
            self.assertTrue(manifest['version'].startswith(version+'.'))
            self.assertIn(name,manifest['images'])
            self.assertEqual(hashlib.sha256((ROOT/'docs/images'/name).read_bytes()).hexdigest(),manifest['images'][name]['webp_sha256'])
    def test_home_reaches_graph_and_voice_as_wiki_pages(self):
        _,pages=render(ROOT)
        self.assertIn('/wiki/Spatial-Graph-Studio',pages['Home.md'])
        self.assertIn('/wiki/Reusable-Voice-Graphs',pages['Home.md'])
if __name__=='__main__':unittest.main()
