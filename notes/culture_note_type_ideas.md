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
 * ~~Collaborating artists (artists that have been featured on each others' tracks)~~
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
 * ~~name+image>similar/collaborating artists~~
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

### Video
#### Fields
 * ~~Name~~
 * ~~Description~~
 * ~~Year released~~
 * Actors & roles
 * Director
 * ~~Poster image~~
 * ~~YouTube trailer video~~
 * Watched?
   * field that differentiates between things you've already watched vs. things that you've flagged as want to see. If you haven't seen it yet, you probably have less knowledge of the item.

#### Cards
 * ~~Poster>Name~~
 * ~~Name>Poster~~
 * ~~Video>Name~~
 * ~~Description>Name~~
 * ~~Name>Description~~
 * Name>Actors+Roles (if watched)
 * Actors+Roles>Name (if watched) 
 * Name>Director (if watched and have 3+ films under management with same director)


### Actor
#### Fields
 * ~~Name~~
 * Birthday
 * ~~Photo~~
 * ~~Films they've been in~~
   * that you've seen + top ~2 from 'well known'? include role?)
 * Co-stars (maybe? to promote more linkages between people)

#### Cards
 * ~~Photo>Name~~
 * ~~Name>Photo~~
 * ~~Name>Films~~
 * ~~Films>Name~~
 * Name>Co-star

## Art
Potential services:
* [Artsy.net](https://www.artsy.net/) (paintings+sculptures, public API. [`collections`](https://developers.artsy.net/v2/docs/collections) endpoint can be used to retrieve a users' favorites)
* [WikiArt.org](https://www.wikiart.org/en) (paintings+sculptures, limited/under construction public API, seemingly not updated since 2017. Does not seem to have endpoint to list favorites / follows of a user)

## Video Games
Potential services:
* [Steam](https://store.steampowered.com/) (some big titles & most indie games, public API)
* [TheGamesDB](https://thegamesdb.net/) (all titles, public API)

## Books
Potential services:
* [Goodreads](https://www.goodreads.com/)