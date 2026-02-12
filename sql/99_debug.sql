/* ============================= */
/* 99_DEBUG — CONTROLES          */
/* ============================= */

-- Vérifier que la table existe
SHOW TABLES IN SCHEMA DB_LAB.CHAT_APP;

-- Voir les 50 derniers messages
SELECT *
FROM DB_LAB.CHAT_APP.CHAT_MESSAGES
ORDER BY timestamp DESC
LIMIT 50;
