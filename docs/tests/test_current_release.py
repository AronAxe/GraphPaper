"""Published guides and screenshots must cover the version they describe."""
import hashlib
import json
from pathlib import Path
import re
import unittest

from graphpaper import __version__
from scripts.docs_tool import configuration, render

ROOT = Path(__file__).resolve().parents[2]


class CurrentDocumentationTests(unittest.TestCase):
    def test_wiki_version_matches_application(self):
        self.assertEqual(configuration(ROOT)['docs_version'], __version__)

    def test_spatial_graph_and_reusable_voice_guides_are_published(self):
        sources = {p['source'] for p in configuration(ROOT)['pages']}
        self.assertTrue({'docs/GRAPH-STUDIO.md', 'docs/VOICE-GRAPHS.md'} <= sources)

    def test_sidebar_sections_are_contiguous(self):
        sections = [p['section'] for p in configuration(ROOT)['pages']]
        runs = [s for i,s in enumerate(sections) if i == 0 or s != sections[i-1]]
        self.assertEqual(len(runs),len(set(runs)), 'Group the sidebar instead of repeating sections')

    def test_readme_screenshots_have_current_capture_provenance(self):
        minor = '.'.join(__version__.split('.')[:2])
        manifest = json.loads((ROOT / f'docs/images/screenshots-v{minor}.json').read_text())
        self.assertEqual(manifest['version'], __version__)
        readme = (ROOT/'README.md').read_text(encoding='utf-8')
        images = re.findall(r'!\[[^\]]*\]\(docs/images/([^)]*\.webp)\)',readme)
        self.assertGreaterEqual(len(images),3)
        for name in images:
            with self.subTest(image=name):
                self.assertIn(name,manifest['images'])
                path = ROOT/'docs/images'/name
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),manifest['images'][name]['webp_sha256'])

    def test_home_reaches_graph_and_voice_as_wiki_pages(self):
        _,pages = render(ROOT)
        home = pages['Home.md']
        self.assertIn('/wiki/Spatial-Graph-Studio',home)
        self.assertIn('/wiki/Reusable-Voice-Graphs',home)


if __name__ == '__main__':
    unittest.main()
