import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('feed',BASE/'scripts/live_youtube_feed.py')
feed=importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)
spec=importlib.util.spec_from_file_location('server',BASE/'dashboard/live_server.py')
server=importlib.util.module_from_spec(spec)
import os
state_dir=tempfile.TemporaryDirectory()
os.environ['DRONEMILL_LIVE_STATE']=state_dir.name
spec.loader.exec_module(server)

NOW=dt.datetime.now(dt.timezone.utc)
FUTURE=(NOW+dt.timedelta(days=5)).isoformat()

def video(vid='newStudio', privacy='private', publish=FUTURE, duration='PT2M28S', portrait=False):
    status={'privacyStatus':privacy,'uploadStatus':'processed'}
    if publish:status['publishAt']=publish
    return {'id':vid,'snippet':{'title':vid,'publishedAt':(NOW-dt.timedelta(days=1)).isoformat(),
                'thumbnails':{'medium':{'url':'https://i.ytimg.com/test.jpg'}}},'status':status,
            'contentDetails':{'duration':duration},'statistics':{'viewCount':'7'},
            'fileDetails':{'videoStreams':[{'widthPixels':720 if portrait else 1280,'heightPixels':1280 if portrait else 720}]}}

class Request:
    def __init__(self,value):self.value=value
    def execute(self):return self.value

class FakeYouTube:
    def __init__(self,videos,channel='anime'):self.data=videos;self.pages=[];self.channel=channel
    def channels(self):return self
    def playlistItems(self):return self
    def videos(self):return self
    def list(self,**kwargs):
        if kwargs.get('mine'):
            return Request({'items':[{'id':feed.CHANNEL_IDS[self.channel],'snippet':{},'contentDetails':{'relatedPlaylists':{'uploads':'uploads'}}}]})
        if 'playlistId' in kwargs:
            page=kwargs.get('pageToken');self.pages.append(page)
            result={'items':[{'contentDetails':{'videoId':v['id']}} for v in self.data[:1] if not page]}
            if not page:result['nextPageToken']='second'
            else:result['items']=[{'contentDetails':{'videoId':v['id']}} for v in self.data[1:]]
            return Request(result)
        return Request({'items':[v for v in self.data if v['id'] in kwargs['id'].split(',')]})

class FeedTests(unittest.TestCase):
    def test_discovers_studio_upload_without_ledger_and_reads_all_pages(self):
        yt=FakeYouTube([video(),video('second')])
        with patch.object(feed,'read_json',return_value=[]):out=feed.snapshot('anime',yt)
        self.assertEqual(len(out['items']),2)
        self.assertEqual(yt.pages,[None,'second'])
    def test_unscheduled_private_and_unlisted_are_excluded(self):
        self.assertIsNone(feed.feed_item(video(publish=None),'anime',{},NOW))
        self.assertIsNone(feed.feed_item(video(privacy='unlisted'),'anime',{},NOW))
    def test_background_check_finds_new_upload_and_rechecks_older_known_schedule(self):
        old=video('olderVid123')
        yt=FakeYouTube([video(),old])
        with patch.object(feed,'read_json',return_value=[{'url':'https://youtu.be/olderVid123','is_future':True}]):
            out=feed.snapshot('anime',yt,recent=True)
        self.assertEqual({i['title'] for i in out['items']},{'newStudio','olderVid123'})
        self.assertEqual(yt.pages,[None])
    def test_wrong_channel_identity_is_rejected(self):
        with self.assertRaises(RuntimeError):
            feed.snapshot('anime',FakeYouTube([],channel='dronemill'))
    def test_timeless_plans_without_youtube_ids_are_preserved_individually(self):
        plans=[{'id':1,'title':'plan one','on_youtube':False}, {'id':2,'title':'plan two','on_youtube':False}]
        with patch.object(feed,'read_json',return_value=plans):
            out=feed.snapshot('dronemill',FakeYouTube([video()],channel='dronemill'))
        self.assertEqual([i['title'] for i in out['items'] if i.get('on_youtube') is False],['plan one','plan two'])
    def test_live_time_and_title_override_old_snapshot(self):
        v=video();item=feed.feed_item(v,'anime',{'title':'old','publish_at':'old'},NOW)
        self.assertEqual(item['publish_at'],FUTURE)
        self.assertEqual(item['title'],'newStudio')
    def test_landscape_148_seconds_remains_regular_video(self):
        self.assertEqual(feed.feed_item(video(),'anime',{},NOW)['kind'],'video')
        self.assertEqual(feed.feed_item(video(portrait=True),'anime',{},NOW)['kind'],'short')
    def test_publication_is_not_a_future_schedule(self):
        self.assertFalse(feed.feed_item(video(privacy='public'),'anime',{},NOW)['is_future'])
    def test_deleted_or_rejected_video_is_excluded(self):
        for status in ['deleted','rejected','failed']:
            v=video();v['status']['uploadStatus']=status
            self.assertIsNone(feed.feed_item(v,'anime',{},NOW))
    def test_failed_api_preserves_last_good_snapshot_as_stale(self):
        server.CACHE['anime']=(0,{'items':[{'title':'keep'}],'stale':False,'updated_at':'old'})
        import subprocess
        with patch.object(server.subprocess,'run',side_effect=subprocess.TimeoutExpired('worker',45)):
            data=server.get_feed('anime',True)
        self.assertTrue(data['stale']);self.assertEqual(data['items'][0]['title'],'keep')
    def test_caching_deduplicates_tabs_but_refresh_bypasses_old_cache(self):
        import time,json,subprocess
        server.CACHE['anime']=(time.monotonic()-10,{'items':[],'stale':False})
        with patch.object(server.subprocess,'run',return_value=subprocess.CompletedProcess('worker',0,json.dumps({'items':[{'title':'fresh'}],'stale':False}))) as run:
            server.get_feed('anime');self.assertFalse(run.called)
            data=server.get_feed('anime',True);self.assertTrue(run.called)
            self.assertEqual(data['items'][0]['title'],'fresh')

if __name__=='__main__':unittest.main()
