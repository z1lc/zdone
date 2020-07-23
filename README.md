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

## Milestones
 * 2019-08-01 [First commit](https://github.com/z1lc/zdone/commit/9f13a15ef013a073b1d2af17abefa08727f73aac)
 * 2019-08-07 [zdone.co](https://www.zdone.co) domain purchased
 * 2019-08-23 [zdone Android app](https://play.google.com/store/apps/details?id=com.cronus.zdone) published
 * 2019-11-23 [Countdown-based tasks UI](https://github.com/z1lc/zdone/commit/01fac561a8405cd2e19080a41c603843a21332fc)
 * 2020-01-14 [MVP](https://github.com/z1lc/zdone/commit/abb8b001be6bcabc156cff96a505d1a4d6f94ecd) for Spotify + Anki
 * 2020-04-14 Spotify + Anki integration [publicly released](https://www.reddit.com/r/Anki/comments/g0zgyc/spotify_anki_learn_to_recognize_songs_by_your/)
 * 2020-05-16 [MVP](https://github.com/z1lc/zdone/commit/2399fe0a2db63664fd22e413f127adb9629a7f1d) for Reminders
 * 2020-06-13 [MVP](https://github.com/z1lc/zdone/commit/278d2f7e5a4611c3547affcaaa428f4cc7df9a12) for Tasks v2
 * 2020-07-16 [MVP](https://github.com/z1lc/zdone/commit/1a728255fd34a1d1e47c8ee822219be0c3538eee) for Movies & TV
