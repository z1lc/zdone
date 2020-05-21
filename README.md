# zdone.co
[![CircleCI](https://circleci.com/gh/z1lc/zdone/tree/master.svg?style=shield)](https://circleci.com/gh/z1lc/zdone/tree/master)
![GitHub last commit](https://img.shields.io/github/last-commit/z1lc/core)

[zdone.co](https://www.zdone.co/) is made up of a few distinct areas of functionality.
 * **Todo system**: a forgiving todo management system focused on recurring tasks. You set up a prioritization for all the things you do, and zdone will use that prioritization, along with data on how overdue a task is and how much time is left in the day, to select the tasks that are most important. Invite-only.
 * **Spotify + Anki**: an integration between [Spotify](https://www.spotify.com/) and [Anki](https://apps.ankiweb.net/) to help you get more into music. Read more about it in the [launch post on Reddit](https://www.reddit.com/r/Anki/comments/g0zgyc/spotify_anki_learn_to_recognize_songs_by_your/). Open for [registration](https://www.zdone.co/register).
 * **TMDb + Anki**: an integration between [TMDb](https://www.themoviedb.org/), [YouTube](https://www.youtube.com/), and [Anki](https://apps.ankiweb.net/) to help you get more into movies & TV shows. Invite-only.

## Code
Much of the templating, user login/session management, and database schema/migration framework follow [The Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) by Miguel Grinberg. Looking at code examples from that tutorial will be helpful in understanding zdone code.

A few dependencies have been forked from their public versions to integrate additional functionality (see requirements.txt):
 * [spotipy](https://github.com/z1lc/spotipy) to allow selecting a custom offset to start songs at
 * [genanki](https://github.com/z1lc/genanki) to allow custom creation dates for notes
 * [Toodledo](https://github.com/z1lc/toodledo-python)
