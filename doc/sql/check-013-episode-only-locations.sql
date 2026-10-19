SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
-- EMBEDDING-UPDATE-013: have the places cited only by episodes reached t2slocations?
-- READ ONLY. ChromaDB is not reachable from SQL, so this checks what decides it:
--   1. process 216 ran AFTER those places were created (its watermark is later), and
--      finished (its current-id variable is empty again);
--   2. how many documents 216 must hold for them, by its own rules: one per language,
--      none for a deleted place or an empty name, and no French document when the
--      French name equals the English one.
-- The exact count in Chroma comes from check-t2slocations-coverage.py.
-- Run: ssh vps-agent run embedding-update/doc/sql/check-013-episode-only-locations.sql

SELECT VAR_NAME, VAR_VALUE, TIM_UPDATED
FROM T_WC_SERVER_VARIABLE
WHERE VAR_NAME LIKE 'strembeddingupdatet2slocation%'
ORDER BY VAR_NAME;

-- The places cited by episodes only (no movie, no series), and when they last changed.
SELECT COUNT(*) AS EPISODE_ONLY_PLACES,
       SUM(DELETED = 0) AS LIVING,
       MIN(ID_LOCATION) AS MIN_ID, MAX(ID_LOCATION) AS MAX_ID,
       MIN(TIM_UPDATED) AS FIRST_UPDATE, MAX(TIM_UPDATED) AS LAST_UPDATE
FROM T_WC_T2S_LOCATION
WHERE COALESCE(EPISODE_COUNT, 0) > 0 AND COALESCE(MOVIE_COUNT, 0) = 0 AND COALESCE(SERIE_COUNT, 0) = 0;

-- Documents 216 must hold for them, by its own rules.
SELECT SUM(TRIM(COALESCE(LOCATION_NAME, '')) <> '') AS EXPECTED_EN_DOCS,
       SUM(TRIM(COALESCE(LOCATION_NAME_FR, '')) <> ''
           AND TRIM(COALESCE(LOCATION_NAME_FR, '')) <> TRIM(COALESCE(LOCATION_NAME, ''))) AS EXPECTED_FR_DOCS
FROM T_WC_T2S_LOCATION
WHERE DELETED = 0
  AND COALESCE(EPISODE_COUNT, 0) > 0 AND COALESCE(MOVIE_COUNT, 0) = 0 AND COALESCE(SERIE_COUNT, 0) = 0;

-- Living places updated after 216's last start: these are the ones it has not seen yet.
SELECT COUNT(*) AS LIVING_PLACES_NEWER_THAN_216_WATERMARK
FROM T_WC_T2S_LOCATION l
JOIN T_WC_SERVER_VARIABLE v ON v.VAR_NAME = 'strembeddingupdatet2slocationstartdatetime'
WHERE l.DELETED = 0 AND l.TIM_UPDATED >= v.VAR_VALUE
  AND COALESCE(l.EPISODE_COUNT, 0) > 0 AND COALESCE(l.MOVIE_COUNT, 0) = 0 AND COALESCE(l.SERIE_COUNT, 0) = 0;

-- Arlington (12674), the acceptance place of the episode tickets.
SELECT ID_LOCATION, LOCATION_NAME, LOCATION_NAME_FR, DELETED, MOVIE_COUNT, SERIE_COUNT, EPISODE_COUNT, TIM_UPDATED
FROM T_WC_T2S_LOCATION WHERE ID_LOCATION = 12674;
