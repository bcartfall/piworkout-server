# piWorkout

piWorkout is a series of Desktop and Mobile applications designed to play a YouTube video on multiple screens synchronized with a workout stopwatch and with allowances for bluetooth audio latency and video latency.

- [piWorkout Server](https://github.com/bcartfall/piworkout-server)
- [piWorkout Desktop](https://github.com/bcartfall/piworkout-desktop)
- [piWorkout Android](https://github.com/bcartfall/piworkout-android)
- [piWorkout iOS](https://github.com/bcartfall/piworkout-ios)

# piWorkout Server 

piWorkout Server is the main server for piWorkout Desktop, piWorkout iOS, and piWorkout Android.

- Downloads correct version of YouTube videos from a playlist.
- Provides API to:
    - Serves streaming video files.
    - Coordinates settings.
    - Coordinates timer.
    - Coordinates latencies.
    - Display list of media.
    
# Dependencies

The docker build will take care of all dependencies.

- Python 3.7 or greater
- python libraries (see backend/requirements.txt)
    
# Instructions

Copy `.env-sample` to `.env` and configure.

- APP_HOST: Main application host. `localhost` or `0.0.0.0`.
- APP_PORT: Main application port.
- VIDEO_FOLDER: Folder where videos will be stored.

Setup YouTube API and URI redirects at https://console.cloud.google.com/getting-started. Download credential file to `backend/client_secret.json`.

YouTube API requires redirect URIs to be a top level domain or localhost. Use a DNS service like https://freedns.afraid.org/ or your own domain to connect with YouTube.

Run server docker containers:

```bash
bash ./run.bash
```

If there have been changes to the react frontend or if you haven't built the react frontend yet run:

```bash
bash ./build_react.bash
```

# Setup

Open the web server in your browser `http://$APP_HOST:$APP_PORT`. Connect the application with your YouTube account. Set the `Playlist URL` in the settings. Copy (optional) your YouTube cookies to enable `Mark as Viewed` support.


# Licence

This project is licensed under GPLv2.

This project installs static libraries from `ffmpeg` (GPLv2).
