INSERT INTO public.app_daily (
    snapshot_date,
    country,
    app_id,
    app_name,
    app_version,
    rating,
    ratings_count,
    primary_genre
)
VALUES (
    :snapshot_date,
    :country,
    :app_id,
    :app_name,
    :app_version,
    :rating,
    :ratings_count,
    :primary_genre
)
ON CONFLICT (snapshot_date, country, app_id)
DO UPDATE SET
    app_name      = EXCLUDED.app_name,
    app_version   = EXCLUDED.app_version,
    rating        = EXCLUDED.rating,
    ratings_count = EXCLUDED.ratings_count,
    primary_genre = EXCLUDED.primary_genre;