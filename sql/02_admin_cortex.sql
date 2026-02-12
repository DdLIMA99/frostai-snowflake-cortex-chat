/* ===================================== */
/* 02_ADMIN_CORTEX — PARAM COMPTE        */
/* ===================================== */

SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;

ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';
