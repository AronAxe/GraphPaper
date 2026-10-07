"""Offline, standard-library-only checks for the docs/wiki maintenance tooling."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.docs_tool import anchors,check,configuration,reconciliation,render,sha,write_pages,MANIFEST


class DocumentationToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/'docs/images').mkdir(parents=True)
        (self.root/'docs/images/header.svg').write_text('<svg/>')
        (self.root/'docs/README.md').write_text('# Home\n\n[Start](START.md#first-steps)\n\n![Header](images/header.svg)\n',encoding='utf-8')
        (self.root/'docs/START.md').write_text('# Start\n\n## First steps\n\n[Home](README.md)\n',encoding='utf-8')
        for name in ['README.md','CONTRIBUTING.md','SECURITY.md']:
            (self.root/name).write_text('# Page\n\n[Guide](docs/README.md)\n',encoding='utf-8')
        self.conf={'repository':'AronAxe/GraphPaper','docs_version':'0.3.0','pages':[{'title':'Home','source':'docs/README.md','section':'Start'},{'title':'Getting-Started','source':'docs/START.md','section':'Start'}]}
        self.save_config()
    def tearDown(self):self.temp.cleanup()
    def save_config(self):(self.root/'docs/wiki-pages.json').write_text(json.dumps(self.conf),encoding='utf-8')
    def test_local_files_and_heading_links_validate(self):
        self.assertEqual(check(self.root)['wiki_pages'],2)
    def test_missing_local_target_is_an_error(self):
        (self.root/'README.md').write_text('[Missing](missing.md)')
        with self.assertRaisesRegex(ValueError,'missing target'):check(self.root)
    def test_missing_heading_is_an_error(self):
        (self.root/'README.md').write_text('[Missing](docs/START.md#absent)')
        with self.assertRaisesRegex(ValueError,'missing heading'):check(self.root)
    def test_fenced_examples_are_not_checked_as_links(self):
        (self.root/'README.md').write_text('```md\n[Example](not-a-real-file.md)\n```\n')
        check(self.root)
    def test_duplicate_titles_rejected(self):
        self.conf['pages'][1]['title']='home';self.save_config()
        with self.assertRaisesRegex(ValueError,'Duplicate'):configuration(self.root)
    def test_path_escape_rejected(self):
        self.conf['pages'][1]['source']='../private.md';self.save_config()
        with self.assertRaisesRegex(ValueError,'Unsafe'):configuration(self.root)
    def test_render_translates_links_images_and_navigation(self):
        conf,pages=render(self.root)
        self.assertIn('https://github.com/AronAxe/GraphPaper/wiki/Getting-Started#first-steps',pages['Home.md'])
        self.assertIn('https://raw.githubusercontent.com/AronAxe/GraphPaper/main/docs/images/header.svg',pages['Home.md'])
        self.assertIn('_Sidebar.md',pages);self.assertIn('_Footer.md',pages)
        self.assertIn('Suggest an edit',pages['Home.md'])
    def test_unmanaged_home_needs_explicit_adoption(self):
        folder=self.root/'wiki';folder.mkdir();(folder/'Home.md').write_text('Original home')
        _,pages=render(self.root)
        with self.assertRaisesRegex(ValueError,'independently edited'):reconciliation(folder,self.conf,pages)
        self.assertEqual(reconciliation(folder,self.conf,pages,True),[])
    def test_managed_page_changes_are_not_overwritten(self):
        folder=self.root/'wiki';folder.mkdir();(folder/'Home.md').write_text('Independent edit')
        (folder/MANIFEST).write_text(json.dumps({'repository':'AronAxe/GraphPaper','files':{'Home.md':sha(b'Old generated text')}}))
        _,pages=render(self.root)
        with self.assertRaisesRegex(ValueError,'independently edited'):reconciliation(folder,self.conf,pages)
    def test_unchanged_managed_pages_can_update(self):
        folder=self.root/'wiki';folder.mkdir();(folder/'Home.md').write_text('Old generated text')
        (folder/'Personal-notes.md').write_text('Keep me')
        (folder/MANIFEST).write_text(json.dumps({'repository':'AronAxe/GraphPaper','files':{'Home.md':sha(b'Old generated text')}}))
        _,pages=render(self.root);removed=reconciliation(folder,self.conf,pages)
        self.assertEqual(removed,[]);write_pages(folder,pages)
        self.assertEqual((folder/'Personal-notes.md').read_text(),'Keep me')
    def test_deleted_generated_pages_must_match_previous_hash(self):
        folder=self.root/'wiki';folder.mkdir();(folder/'Old-page.md').write_text('Old generated text')
        (folder/MANIFEST).write_text(json.dumps({'repository':'AronAxe/GraphPaper','files':{'Old-page.md':sha(b'Old generated text')}}))
        self.assertEqual(reconciliation(folder,self.conf,{'Home.md':'New'}),['Old-page.md'])
    def test_heading_slug_duplicates_and_punctuation(self):
        self.assertEqual(anchors('# Models & reasoning\n## Setup\n## Setup\n'),{'models--reasoning','setup','setup-1'})


if __name__=='__main__':unittest.main()
