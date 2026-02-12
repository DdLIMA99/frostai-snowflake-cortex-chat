# FrostAI — Chat Streamlit in Snowflake + Cortex + Historique

FrostAI est une application de chat type ChatGPT, hébergée dans **Streamlit in Snowflake**, qui interroge un **LLM Snowflake Cortex** sans clé OpenAI.  
Les conversations sont stockées dans Snowflake (table `CHAT_MESSAGES`) pour assurer la persistance.

## Démo
- Application Snowflake (Streamlit in Snowflake) : **[mettre le lien ici]**
- Capture : `assets/screenshots/app.png`

## Architecture
1. **Streamlit in Snowflake** : interface chat (sidebar + messages + saisie)
2. **Snowflake Cortex** : génération de réponse via `SNOWFLAKE.CORTEX.COMPLETE`
3. **Snowflake Table** : persistance des messages (user/assistant)

Flux :
- User → UI → build prompt (system + historique) → Cortex → réponse → UI
- User/Assistant → INSERT dans `DB_LAB.CHAT_APP.CHAT_MESSAGES`

## Prérequis Snowflake
- Warehouse disponible
- Droits création DB/Schema
- Streamlit in Snowflake activé
- Cortex activé

### Activer Cortex cross-region (si nécessaire)
```sql
SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;
ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';
