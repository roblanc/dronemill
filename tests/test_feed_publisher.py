import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('publisher',Path(__file__).resolve().parents[1]/'scripts/publish-live-feed.py')
publisher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

class PublisherTests(unittest.TestCase):
    def test_public_feed_contains_only_approved_display_fields(self):
        data={'channel':'anime','updated_at':'time','avatar':'https://example.com/avatar',
              'items':[{'title':'scheduled','url':'https://youtu.be/123','publish_at':'later','duration':'PT2M',
                        'description':'must stay off this feed','tags':['private'],'local_source':'private path'},
                       {'title':'unuploaded plan','on_youtube':False}]}
        out=publisher.public_snapshot(data)
        self.assertEqual(len(out['items']),1)
        self.assertEqual(set(out['items'][0]),{'title','url','publish_at','duration'})
    def test_finished_record_change_triggers_watcher_even_after_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'published.json';path.write_text('[]')
            with patch.object(publisher,'SOURCES',[path]):
                first=publisher.versions()
                replacement=Path(directory)/'new.json';replacement.write_text('[{"id":"new"}]');replacement.replace(path)
                self.assertNotEqual(first,publisher.versions())
    def test_unchanged_record_does_not_trigger_extra_work(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'published.json';path.write_text('[]')
            with patch.object(publisher,'SOURCES',[path]):
                self.assertEqual(publisher.versions(),publisher.versions())

if __name__=='__main__':unittest.main()
