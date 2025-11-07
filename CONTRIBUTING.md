# Come Contribuire

Grazie per l'interesse a contribuire al Meta Ads MCP Server! Ecco come puoi aiutare.

## Segnalare Bug

Se trovi un bug, apri una issue su GitHub includendo:

1. Descrizione chiara del problema
2. Passaggi per riprodurre il bug
3. Comportamento atteso vs comportamento effettivo
4. Versione Python e dipendenze
5. Messaggio d'errore completo (se presente)

## Proporre Nuove Funzionalità

Per suggerire nuove feature:

1. Apri una issue descrivendo la funzionalità
2. Spiega il caso d'uso e perché sarebbe utile
3. Fornisci esempi di come dovrebbe funzionare

## Pull Request

### Setup Sviluppo

```bash
# Clona il repo
git clone https://github.com/yourusername/meta-ads-mcp-server.git
cd meta-ads-mcp-server

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# oppure
.\venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt

# Configura token di test
export META_ACCESS_TOKEN="your_test_token"
```

### Linee Guida

1. **Codice**:
   - Segui PEP 8 per lo stile Python
   - Usa type hints per tutte le funzioni
   - Documenta con docstring dettagliati
   - Mantieni funzioni sotto 50 righe quando possibile

2. **Commit**:
   - Messaggi chiari e descrittivi
   - Un commit per feature/fix logico
   - Formato: `tipo: descrizione breve`
     - Tipi: feat, fix, docs, style, refactor, test

3. **Testing**:
   - Testa il codice con dati reali (se possibile)
   - Verifica che `python -m py_compile meta_ads_mcp.py` passi
   - Controlla che il server si avvii senza errori

4. **Documentazione**:
   - Aggiorna README.md se necessario
   - Aggiungi esempi d'uso per nuovi tool
   - Documenta parametri e return types

### Processo PR

1. Fork il repository
2. Crea un branch per la tua feature (`git checkout -b feature/nuova-feature`)
3. Commit delle modifiche (`git commit -am 'feat: aggiungi nuova feature'`)
4. Push al branch (`git push origin feature/nuova-feature`)
5. Apri una Pull Request su GitHub

## Aree di Contributo

Alcune idee su dove contribuire:

- **Nuovi tool**: Implementare altri endpoint Meta API
- **Testing**: Aggiungere test automatizzati
- **Documentazione**: Migliorare esempi e guide
- **Performance**: Ottimizzare chiamate API e gestione dati
- **UX**: Migliorare formattazione output e messaggi errore
- **Internazionalizzazione**: Supporto per altre lingue

## Domande?

Se hai domande, apri una discussion su GitHub o contattaci via email.

Grazie per il tuo contributo! 🚀
