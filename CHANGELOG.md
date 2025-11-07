# Changelog

Tutte le modifiche significative al progetto sono documentate qui.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

## [1.1.0] - 2025-11-07

### Aggiunto
- Supporto per **date range personalizzati** nei tool `meta_ads_get_insights` e `meta_ads_generate_report`
- Nuovi parametri `since` e `until` per specificare intervalli temporali custom (formato YYYY-MM-DD)
- Validazione automatica che assicura la presenza di entrambe le date (since + until)
- Documentazione estesa con esempi di utilizzo date personalizzate

### Modificato
- I parametri `date_preset` sono ora opzionali quando si usano date personalizzate
- Migliorata visualizzazione periodo nei report (mostra preset o range custom)
- Aggiornate docstring con esempi di date personalizzate

### Note
- Se specifichi `since` e `until`, il `date_preset` viene automaticamente ignorato
- Range massimo supportato: 37 mesi (con limitazioni per alcuni breakdown)
- Formato date richiesto: YYYY-MM-DD (es. "2025-01-01")

## [1.0.0] - 2025-11-07

### Aggiunto
- MCP Server iniziale per Meta Marketing API
- Tool `meta_ads_list_accounts` per elencare account pubblicitari
- Tool `meta_ads_list_campaigns` per listare campagne
- Tool `meta_ads_list_adsets` per listare ad set
- Tool `meta_ads_list_ads` per listare annunci
- Tool `meta_ads_get_insights` per metriche di performance
- Tool `meta_ads_get_creative` per dettagli creativi degli annunci
- Tool `meta_ads_generate_report` per report con breakdown demografici
- Supporto per formato output Markdown e JSON
- Gestione errori completa con messaggi educativi
- Validazione input con Pydantic v2
- Documentazione completa nel README con guida token Meta
- File di configurazione esempio (.env.example)

### Caratteristiche
- Compatibile con Claude Code CLI
- Support per tutti i principali breakdown (età, genere, paese, placement)
- Preset temporali flessibili (last_7d, last_30d, this_month, ecc.)
- Character limit per prevenire risposte troppo lunghe
- Formattazione valuta automatica (centesimi → EUR/USD)
- Metriche complete: impressions, clicks, spend, CTR, CPC, conversions, ROAS

[1.1.0]: https://github.com/yourusername/meta-ads-mcp-server/releases/tag/v1.1.0
[1.0.0]: https://github.com/yourusername/meta-ads-mcp-server/releases/tag/v1.0.0
