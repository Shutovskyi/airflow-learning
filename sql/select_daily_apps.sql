SELECT DISTINCT app_id
FROM public.tracked_apps
WHERE track_daily = true
  AND app_id IS NOT NULL
ORDER BY app_id;