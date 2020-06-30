# Future Anki Culture note types
see [Whimsical](https://whimsical.com/WKr5BEqNM9EgYW9nE76vvc) for ideas


## Music
### Artist
#### Fields
 * ~~Name~~
 * ~~Songs (only ones you have listened to)~~
 * ~~Albums (only ones you have listened to, includes years)~~
 * Genres
 * Similar artists
   * only other artists you also follow? or those are at least prioritized vs. listing others?
 * Collaborating artists (artists that have been featured on each others' tracks)
   * potentially easier to recall?
 * Years active
   * based on album release dates?
 * ~~Image (sourced from Spotify / provided backup image if one from Spotify sucks)~~

#### Cards
 * ~~image>name~~
 * ~~name>image~~
 * ~~name+image>song~~ (currently not using, since doesn't seem all that valuable)
 * ~~songs>name~~
 * ~~name+image>albums~~
 * ~~albums>name+image~~
 * name+image>genres
 * name+image>similar/collaborating artists
   * similar artists that you also track bolded/green?
 * name+image>years active
   * could get annoying with years?
 * years active+genres>name+image

### Album
Generally, probably fine to wait to add this card until the user has listened to 3+ songs from that album. This doesn't deal with the issue of a new release from an artist whose songs don't get popular, or which is a live album (think, RÜFÜS DU SOL's *Live from Joshua Tree*). So alternative might be, for followed artists go ahead and add all albums that are 'real' albums (labeled as such in the Spotify API). Not clear this would solve the example given, or if it's even worth it though. 
#### Fields
 * Name
 * Artist
 * Songs
 * Image

#### Cards
 * Image>Name
 * Name>Image (visualize)
 * Name+Image>Artist

### Genre
#### Fields
 * Name
 * Artists (once you have 3+ artists)

#### Cards
 * name>artists
   * Ex. "name an artist part of the **pop** genre"

## Movies/TV
Potential services:
* [TMDb](https://www.themoviedb.org/) (Movies+TV, public API)
* [Letterboxd](https://letterboxd.com/) (Movies, invite-only API)
* [Mubi](https://mubi.com/) (Movies, undocumented API)

### Fields
 * Name
 * Actors (+ roles?)
 * Poster Image
 * Video
   * Limitation: YouTube videos can autoplay only as muted. May not be a big deal/even a benefit if trailers have voiceovers that give away the movie. Either way, probably fine for MVP.

### Cards
 * Name>Actors
 * Actors+Roles>Name
 * Poster>Name
 * Name>Poster
 * Video>Name 