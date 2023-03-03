from yt_dlp.extractor.youtube import YoutubeIE

from yt_dlp.utils import (
    get_first,
    url_or_none,
)
import model
import json

class PiWorkoutPluginIE(YoutubeIE, plugin_name='piworkout'):
    """
    We set mark_watched to True in options so that when the video is playing we can update the position that has been watched on youtube in realtime
    """
    def _mark_watched(self, video_id, player_responses):
        data = {}
        for is_full, key in enumerate(('videostatsPlaybackUrl', 'videostatsWatchtimeUrl')):
            url = get_first(player_responses, ('playbackTracking', key, 'baseUrl'),
                            expected_type=url_or_none)
            data[key] = {
                'is_full': is_full,
                'url': url,
            }
        
        # save urls to video model
        video = model.video.byVideoId(videoId=video_id)
        video.watchedUrl = json.dumps(data)
        model.video.save(video=video)
         
        # do NOT continue with super mark_watched. We do not want the video mark as 100% watched
        #return super()._mark_watched(video_id, player_responses)
