/* ============================= */
/* 00_SETUP — ENVIRONNEMENT      */
/* ============================= */

-- 1) Warehouse
CREATE WAREHOUSE IF NOT EXISTS WH_LAB
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- 2) Database + Schema
CREATE DATABASE IF NOT EXISTS DB_LAB;
CREATE SCHEMA IF NOT EXISTS DB_LAB.CHAT_APP;

-- 3) Contexte
USE WAREHOUSE WH_LAB;
USE DATABASE DB_LAB;
USE SCHEMA CHAT_APP;

-- 4) Stage (optionnel, utile si tu ajoutes des fichiers plus tard)
CREATE STAGE IF NOT EXISTS CHAT_APP_STAGE;

-- 5) Vérifs contexte
SELECT CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA();

-- 6) Test Cortex (lecture seule)
SELECT SNOWFLAKE.CORTEX.TRY_COMPLETE(
  'mistral-large',
  'Dis bonjour en une phrase.'
) AS TEST_CORTEX;
