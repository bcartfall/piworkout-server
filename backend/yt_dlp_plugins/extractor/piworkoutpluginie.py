from yt_dlp.extractor.youtube import YoutubeIE

from yt_dlp.utils import (
    get_first,
    url_or_none,
)
import urllib.error
import urllib.parse
import random

# ⚠ Other plugins cannot be overridden using this method
# ⚠ The extractor internals may change without warning, breaking the plugin

class PiWorkoutPluginIE(YoutubeIE, plugin_name='piworkout'):
    def _real_extract(self, url):
        self.to_screen('Passing through PiWorkoutPluginIE')
        return super()._real_extract(url)
    
    def _mark_watched(self, video_id, player_responses):
        print('_mark_watched() Passing through PiWorkoutPluginIE')
        for is_full, key in enumerate(('videostatsPlaybackUrl', 'videostatsWatchtimeUrl')):
            label = 'fully ' if is_full else ''
            url = get_first(player_responses, ('playbackTracking', key, 'baseUrl'),
                            expected_type=url_or_none)
            if not url:
                self.report_warning(f'Unable to mark {label}watched')
                return
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)

            # cpn generation algorithm is reverse engineered from base.js.
            # In fact it works even with dummy cpn.
            CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
            cpn = ''.join(CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(0, 16))

            # # more consistent results setting it to right before the end
            video_length = [str(float((qs.get('len') or ['1.5'])[0]) - 1)]

            qs.update({
                'ver': ['2'],
                'cpn': [cpn],
                'cmt': video_length,
                'el': 'detailpage',  # otherwise defaults to "shorts"
            })

            if is_full:
                # these seem to mark watchtime "history" in the real world
                # they're required, so send in a single value
                qs.update({
                    'st': 0,
                    'et': video_length,
                })

            url = urllib.parse.urlunparse(
                parsed_url._replace(query=urllib.parse.urlencode(qs, True)))

            ## todo record mark as watched url to use later in player.py
            #print(553, 'mark as watched url=' + url)

            self._download_webpage(
                url, video_id, f'Marking {label}watched',
                'Unable to mark watched', fatal=False)
        #return super()._mark_watched(video_id, player_responses)
    
        