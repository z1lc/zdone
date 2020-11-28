insert into youtube_video_overrides (video_id, youtube_trailer_key)
values ('zdone:video:tmdb:1104', 'RTMk-xy2dTY');

insert into tasks (user_id, title, description, ideal_interval, last_completion, defer_until)
values (1,
        '', --title
        '', --description
        7, --ideal interval
        current_date, --last completion
        NULL --defer until
)
;

-- Number of notifications sent per reminder for user (only includes active)
select title, message, min(sent_at) as first_notification, max(sent_at) as last_notification,
    sum(case when sent_at is not null then 1 else 0 end) as total_notifications
from reminders
         left join reminder_notifications rn on reminders.id = rn.reminder_id
         join users u on reminders.user_id = u.id
where username = 'rsanek' and active
group by 1, 2
order by total_notifications desc, last_notification desc
;

-- Next artists to consider following, ordered by number of plays by friends
select sa.name, count(*)
from spotify_plays
         join spotify_tracks on spotify_plays.spotify_track_uri = spotify_tracks.uri
         join spotify_artists sa on spotify_tracks.spotify_artist_uri = sa.uri
where user_id <= 6 and user_id > 1 and
        spotify_artist_uri not in (
        select spotify_artist_uri
        from managed_spotify_artists
        where user_id = 1
    )
group by 1
order by 2 desc
;

-- Leaderboard
with hn as (select u2.username, count(*) as total_hn_reads
            from hn_read_logs
                     join users u2 on hn_read_logs.user_id = u2.id
            group by 1),
    tasks_summary as (select username,
                          count(*) as total_tasks_completed
                      from task_logs tl
                               join users u3 on tl.user_id = u3.id
                      where tl.action = 'complete'
                      group by 1
    ),
    reminders_summary as (select username,
                              count(*) as reminders
                          from reminders r
                                   join users u4 on r.user_id = u4.id
                          where active
                          group by 1
    ),
    managed_artists as (select username, count(*) as managed_artists
                        from managed_spotify_artists
                                 join users u5 on managed_spotify_artists.user_id = u5.id
                        where following
                        group by 1),
    managed_vids as (select username, count(*) as managed_videos
                     from managed_videos
                              join users u6 on managed_videos.user_id = u6.id
                     group by 1),
    grouped as (select u.id,
                    username,
                    count(distinct spotify_track_uri) as distinct_count,
                    count(*) as total_count,
                    min(created_at) as first_listened,
                    max(created_at) as last_listened
                from spotify_plays
                         right join users u on spotify_plays.user_id = u.id
                where u.spotify_token_json is not null and user_id <> 6
                group by 1)
select grouped.id,
    grouped.username,
    distinct_count as unique_songs,
    total_count as total_plays,
    first_listened::date,
    last_listened::date,
    managed_artists,
    managed_videos,
    reminders as total_reminders,
--     round(total_count * 1.0 / greatest(distinct_count, 1), 2) as plays_per_song,
    total_hn_reads as hn_articles_read,
    total_tasks_completed as tasks_completed
from grouped
         full outer join managed_artists on managed_artists.username = grouped.username
         full outer join managed_vids on managed_vids.username = grouped.username
         full outer join hn on hn.username = grouped.username
         full outer join tasks_summary on tasks_summary.username = grouped.username
         full outer join reminders_summary on reminders_summary.username = grouped.username
where total_count > 1
order by 3 desc, 4 desc, 5 asc
;

-- My 'mature' artists -- those with at least 20 plays
select sa.name, count(*)
from spotify_plays
         join spotify_tracks st on spotify_plays.spotify_track_uri = st.uri
         join spotify_artists sa on st.spotify_artist_uri = sa.uri
where user_id = 1
group by 1
having count(*) >= 30;

--Artists that need images
select sa.uri, sa.name, sa.spotify_image_url
from spotify_plays sp
         join spotify_tracks st on sp.spotify_track_uri = st.uri
         join spotify_features sf on st.uri = sf.spotify_track_uri
         join spotify_artists sa on sf.spotify_artist_uri = sa.uri
where (good_image <> true and image_override_name is null) and user_id <= 6 and
        sa.name not in (
                        'European Brandenburg Ensemble',
                        'KOA',
                        'N. Reyes',
                        'Alexander Peskanov',
                        'Los Angeles Philharmonic',
                        'Philadelphia Orchestra',
                        'Royal Philharmonic Orchestra',
                        'Academy of St. Martin in the Fields',
                        'Boston Pops Orchestra',
                        'London Philharmonic Orchestra',
                        'London Symphony Orchestra',
                        'Wiener Philharmoniker',
                        'Berliner Philharmoniker',
                        'English Chamber Orchestra',
                        'London Philharmonic Choir'
        )
group by 1, 2, 3
having count(distinct st.uri) >= 3
order by min(sp.created_at);


update spotify_artists
set good_image = true
where uri in ('spotify:artist:0TnOYISbd1XYRBk9myaseg');
;


-- New album releases
select sal.name, sa.name, min(sal.released_at)
from spotify_albums sal
         join spotify_artists sa on sal.spotify_artist_uri = sa.uri
         join managed_spotify_artists msa on sa.uri = msa.spotify_artist_uri
where msa.user_id = 1 and released_at >= '2020-04-01' and sal.album_type = 'album' and
    sa.name != 'Ludwig van Beethoven' and sa.name != 'Antonín Dvořák'
group by 1, 2
order by 3 desc;

select title, ideal_interval,
        at - LAG(at)
             OVER (ORDER BY t.id, at ) AS difference
from tasks t
         join task_logs tl on t.id = tl.task_id
where t.user_id = 1 and action = 'complete';


with tasks_selected as (select task_id from task_logs group by task_id having count(task_id) > 1),
    differences as (select title, ideal_interval,
                            at - LAG(at)
                                 OVER (ORDER BY t.id, at ) AS difference
                    from tasks t
                             join task_logs tl on t.id = tl.task_id
                    where t.user_id = 1 and action = 'complete' and t.id in (select task_id from tasks_selected)),
    interval_comparison as (select title, min(ideal_interval) as ideal_interval,
                                extract(day from avg(difference)) as actual_interval
                            from differences
                            where difference > interval '1 day'
                            group by 1)
select avg(actual_interval / ideal_interval) as factor
from interval_comparison
order by factor desc;



with credits as (select * from video_credits where person_id = 'zdone:person:tmdb:13240')
select vp.name, v.id
from video_persons vp
         join video_credits vc on vp.id = vc.person_id
         join videos v on vc.video_id = v.id
         full outer join managed_videos mv on v.id = mv.video_id
where v.id in (select credits.video_id from credits) and vc.person_id != 'zdone:person:tmdb:13240' and mv.user_id = 1
group by 1, 2;

with my_follows as (select * from managed_spotify_artists where following and user_id = 1)
select uri, name, claimed_sales
from best_selling_artists bsa
         left join my_follows mf on mf.spotify_artist_uri = bsa.artist_uri
         left join spotify_artists sa on bsa.artist_uri = sa.uri
where not following or following is null
order by claimed_sales desc
;

--Completed Trello tasks (non-recurring)
select at, task_name
from task_logs
where user_id = 1 and task_id is null and action = 'complete'
and at >= '2020-11-26'
order by at desc
