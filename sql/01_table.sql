/* ============================= */
/* 01_TABLE — PERSISTANCE        */
/* ============================= */

USE DATABASE DB_LAB;
USE SCHEMA CHAT_APP;

CREATE TABLE IF NOT EXISTS CHAT_MESSAGES (
  conversation_id STRING,
  timestamp TIMESTAMP,
  role STRING,
  content STRING
);

SHOW TABLES IN SCHEMA DB_LAB.CHAT_APP;
