# zdone.co
[![CircleCI](https://circleci.com/gh/z1lc/zdone/tree/master.svg?style=shield)](https://circleci.com/gh/z1lc/zdone/tree/master)
![GitHub last commit](https://img.shields.io/github/last-commit/z1lc/zdone)

[zdone.co](https://www.zdone.co/) is made up of a few distinct areas of functionality.
 * **Cultural enrichment system**: integrations between [Anki](https://apps.ankiweb.net/) & external services to promote cultural knowledge.
   * **Music**: uses [Spotify](https://www.spotify.com/) to help you get more into music. Read more about it in the [launch post on Reddit](https://www.reddit.com/r/Anki/comments/g0zgyc/spotify_anki_learn_to_recognize_songs_by_your/). Open for [registration](https://www.zdone.co/register).
   * **Movies & TV**: uses [TMDb](https://www.themoviedb.org/) and [YouTube](https://www.youtube.com/) to help you get more into movies & TV shows. Invite-only.
   * **Books**: uses [Goodreads](https://www.goodreads.com/) to help you get more into reading. Invite-only.
   * Future planned categories include **Art** and **Video Games** 
 * **Todo system**: a forgiving todo management system focused on recurring tasks. You set up a recurrence interval for all your tasks, and zdone will prioritize your tasks based on how overdue they are. Invite-only.
 * **Reminder system**: a low-touch way to consistently remind yourself of arbitrary thoughts over time. You set up a list of such reminders, and zdone will notify you via push notifications on a daily basis. Invite-only.

## Code
Much of the templating, user login/session management, and database schema/migration framework follow [The Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) by Miguel Grinberg. Looking at code examples from that tutorial will be helpful in understanding zdone code.

A few dependencies have been forked from their public versions to integrate additional functionality (see requirements.txt):
 * [spotipy](https://github.com/z1lc/spotipy) to allow selecting a custom offset to start songs at
 * [genanki](https://github.com/z1lc/genanki) to allow custom creation dates for notes
 * [Toodledo](https://github.com/z1lc/toodledo-python)
