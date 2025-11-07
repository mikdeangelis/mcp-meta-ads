# Meta Ads MCP Server

Server MCP (Model Context Protocol) per gestire e analizzare campagne pubblicitarie Facebook/Instagram tramite Meta Marketing API.

## Caratteristiche

Il server fornisce tool completi per:

- ✅ **Elencare risorse**: Account, campagne, ad set e ads
- ✅ **Metriche performance**: Impressions, clicks, spend, CTR, CPC, conversions, ROAS
- ✅ **Dettagli creative**: Testi, immagini, link, CTA degli annunci
- ✅ **Report avanzati**: Breakdown per età, genere, paese, regione, placement

## Prerequisiti

- Python 3.10 o superiore
- Account Meta Business/Developer
- Access token Meta con permessi adeguati

## Installazione

### 1. Clona o scarica il progetto

```bash
git clone <your-repo>
cd meta-ads-mcp-server
```

### 2. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3. Ottieni il token di accesso Meta

Segui questa guida passo-passo per ottenere il tuo access token:

#### A. Crea un'App Meta Developer

1. Vai su [Facebook Developers](https://developers.facebook.com/)
2. Accedi con il tuo account Facebook
3. Clicca su **"My Apps"** → **"Create App"**
4. Seleziona tipo app: **"Business"**
5. Inserisci i dettagli dell'app e conferma

#### B. Aggiungi Marketing API

1. Nel dashboard della tua app, trova **"Marketing API"** nella lista prodotti
2. Clicca su **"Set Up"**
3. La Marketing API apparirà ora nel menu laterale

#### C. Genera Access Token

**Metodo 1: Tool di Access Token (più veloce)**

1. Nel menu laterale, vai su **"Marketing API"** → **"Tools"**
2. Trova la sezione **"Access Token Tool"**
3. Seleziona i permessi necessari:
   - `ads_management` (per gestione completa)
   - `ads_read` (minimo, solo lettura)
   - `read_insights` (per metriche)
4. Clicca su **"Generate Token"**
5. Copia il token generato

**Metodo 2: Graph API Explorer (più controllo)**

1. Vai su [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Seleziona la tua app dal menu a tendina
3. Clicca su **"Get User Access Token"**
4. Seleziona i permessi:
   - `ads_management`
   - `ads_read`
   - `read_insights`
5. Clicca su **"Generate Access Token"** nel Graph API Explorer
6. Autorizza l'app e copia il token

#### D. Converti in Long-Lived Token (Raccomandato)

Il token generato sopra è **short-lived** (scade in poche ore). Per un token che dura **60 giorni**:

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token" \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

Sostituisci:
- `YOUR_APP_ID`: ID della tua app (Dashboard → Settings → Basic)
- `YOUR_APP_SECRET`: App Secret (Dashboard → Settings → Basic)
- `YOUR_SHORT_LIVED_TOKEN`: Il token ottenuto al punto C

La risposta conterrà il long-lived token.

**Alternative: System User Token (non scade)**

Per token permanenti, configura un [System User](https://developers.facebook.com/docs/marketing-api/guides/smb/system-user-access-token-handling/) nel Business Manager. Questo approccio è più complesso ma ideale per produzione.

#### E. Configura la variabile d'ambiente

Una volta ottenuto il token, configuralo:

**Linux/macOS:**
```bash
export META_ACCESS_TOKEN="your_token_here"
```

**Windows (PowerShell):**
```powershell
$env:META_ACCESS_TOKEN="your_token_here"
```

**Persistente (consigliato):**

Aggiungi al tuo file `~/.bashrc` o `~/.zshrc`:
```bash
export META_ACCESS_TOKEN="your_token_here"
```

Poi ricarica: `source ~/.bashrc`

### 4. Verifica il token

Puoi verificare che il token funzioni:

```bash
curl "https://graph.facebook.com/v21.0/me?access_token=YOUR_TOKEN"
```

Dovresti vedere i dettagli del tuo profilo Facebook.

## Configurazione per Claude Code

Per usare il server con Claude Code CLI, aggiungi questa configurazione al file `claude_desktop_config.json`:

**Linux/macOS:** `~/.config/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "python",
      "args": [
        "/path/to/meta-ads-mcp-server/meta_ads_mcp.py"
      ],
      "env": {
        "META_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

Sostituisci:
- `/path/to/meta-ads-mcp-server/` con il percorso effettivo
- `your_token_here` con il tuo access token

## Uso

### Tool disponibili

#### 1. `meta_ads_list_accounts`
Elenca tutti gli account pubblicitari disponibili.

```python
# Esempio risposta
Account Pubblicitari Meta

## Nome Account (act_123456789)
- Valuta: EUR
- Stato: ACTIVE
- Timezone: Europe/Rome
```

#### 2. `meta_ads_list_campaigns`
Lista le campagne di un account.

**Parametri:**
- `account_id`: ID account (formato `act_123456789`)
- `limit`: Numero massimo risultati (default: 25)

```python
# Esempio uso
"Mostrami tutte le campagne dell'account act_123456789"
```

#### 3. `meta_ads_list_adsets`
Lista gli ad set di una campagna.

**Parametri:**
- `campaign_id`: ID campagna
- `limit`: Numero massimo risultati

#### 4. `meta_ads_list_ads`
Lista gli annunci di un ad set.

**Parametri:**
- `adset_id`: ID ad set
- `limit`: Numero massimo risultati

#### 5. `meta_ads_get_insights`
Ottieni metriche di performance dettagliate.

**Parametri:**
- `object_id`: ID dell'oggetto (account, campagna, ad set, ad)
- `level`: Livello aggregazione (`account`, `campaign`, `adset`, `ad`)
- `date_preset`: Periodo preset (`last_7d`, `last_30d`, `this_month`, ecc.)
- `since`: Data inizio custom (formato YYYY-MM-DD, es. '2025-01-01')
- `until`: Data fine custom (formato YYYY-MM-DD, es. '2025-01-31')
- `time_increment`: Granularità giorni (1 = giornaliero)

**Note:** Se specifichi `since` e `until`, il `date_preset` viene ignorato. Puoi usare date personalizzate per analizzare periodi specifici (fino a 37 mesi).

**Metriche restituite:**
- Impressions, Clicks, Spend
- CPM, CPC, CTR
- Reach, Frequency
- Conversions (se configurate)

```python
# Esempi con preset
"Mostrami le performance dell'account nell'ultimo mese"
"Quanto ho speso questa settimana sulla campagna 123?"
"Dammi i dati giornalieri dell'ultima settimana per questo ad set"

# Esempi con date personalizzate
"Mostrami le metriche dal 1 gennaio al 31 gennaio 2025"
"Analizza le performance dal 2024-12-01 al 2024-12-31"
"Dammi i dati giornalieri dal 2025-01-15 al 2025-01-22"
```

#### 6. `meta_ads_get_creative`
Recupera dettagli completi del creative di un annuncio.

**Parametri:**
- `ad_id`: ID annuncio

**Informazioni restituite:**
- Titolo e body text
- Link URL e Call-to-Action
- Image/video reference
- Configurazione placement (Facebook, Instagram)

```python
# Esempio
"Mostrami il creative dell'annuncio 123456789"
```

#### 7. `meta_ads_generate_report`
Genera report avanzati con breakdown demografici e geografici.

**Parametri:**
- `object_id`: ID oggetto da analizzare
- `breakdowns`: Lista dimensioni (`age`, `gender`, `country`, `publisher_platform`, ecc.)
- `date_preset`: Periodo analisi preset
- `since`: Data inizio custom (formato YYYY-MM-DD)
- `until`: Data fine custom (formato YYYY-MM-DD)

**Note:** Supporta sia preset temporali che date personalizzate. Range massimo 394 giorni per breakdown con Reach.

**Breakdown disponibili:**
- `age`: Fasce d'età (18-24, 25-34, 35-44, 45-54, 55-64, 65+)
- `gender`: Genere (male, female)
- `country`: Paese (codice ISO)
- `region`: Regione geografica
- `publisher_platform`: Placement (Facebook, Instagram, Messenger)
- `device_platform`: Device (mobile, desktop)

```python
# Esempi con preset
"Mostrami le performance per fascia d'età e genere negli ultimi 30 giorni"
"Quale paese ha il CTR migliore?"
"Come performano gli annunci su Instagram vs Facebook?"

# Esempi con date personalizzate
"Report per genere dal 1 dicembre al 31 dicembre 2024"
"Breakdown per paese dal 2025-01-01 al 2025-01-31"
"Analizza età e placement dal 2024-12-15 al 2025-01-15"
```

### Esempi conversazionali

```
User: Ciao, quali account pubblicitari ho disponibili?
Claude: [usa meta_ads_list_accounts]

User: Mostrami le campagne dell'account act_123456789
Claude: [usa meta_ads_list_campaigns con account_id=act_123456789]

User: Quanto ho speso nell'ultima settimana sulla campagna 987654321?
Claude: [usa meta_ads_get_insights con campaign_id=987654321, date_preset=last_7d]

User: Analizza le performance per età e genere dell'ad set 555666777 negli ultimi 30 giorni
Claude: [usa meta_ads_generate_report con adset_id=555666777, breakdowns=[age, gender]]
```

## Struttura Gerarchica Meta Ads

```
Account Pubblicitario (act_XXXXX)
└── Campagna (Campaign)
    ├── Obiettivo (CONVERSIONS, TRAFFIC, ecc.)
    ├── Budget campagna
    └── Ad Set
        ├── Budget ad set
        ├── Targeting
        ├── Placement
        └── Annuncio (Ad)
            └── Creative
                ├── Testo
                ├── Immagine/Video
                ├── Link
                └── CTA
```

## Limiti e Note

- **Rate Limiting**: L'API Meta ha limiti di richieste. Se ricevi errore 429, attendi qualche minuto.
- **Token Expiration**: I token short-lived scadono rapidamente, usa long-lived token.
- **Permessi**: Assicurati che il token abbia i permessi necessari (`ads_read` minimo).
- **Dati storici**: Alcuni breakdown hanno limiti temporali (es. 394 giorni per reach con breakdown demografici).
- **Privacy**: Segmenti con pochi dati potrebbero non essere mostrati per protezione privacy.

## Troubleshooting

### Errore: "META_ACCESS_TOKEN non trovato"
Assicurati di aver configurato la variabile d'ambiente correttamente.

### Errore: "Token non valido o scaduto"
Il token è scaduto. Genera un nuovo token seguendo la guida sopra.

### Errore: "Permessi insufficienti"
Il token non ha i permessi necessari. Rigenera il token includendo:
- `ads_management` (per gestione completa)
- `ads_read` (minimo)
- `read_insights` (per metriche)

### Errore: "Risorsa non trovata"
Verifica che l'ID fornito sia corretto. Gli account devono avere prefisso `act_`.

### Errore: "Rate limit raggiunto"
Hai superato il limite di richieste API. Attendi 5-10 minuti prima di riprovare.

## Risorse Utili

- [Meta Marketing API Documentation](https://developers.facebook.com/docs/marketing-apis/)
- [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [Meta Business Help Center](https://www.facebook.com/business/help)
- [Insights API Reference](https://developers.facebook.com/docs/marketing-api/insights/)

## Contributi

Sentiti libero di aprire issue o pull request per miglioramenti o bug fix.

## Licenza

MIT License - vedi file LICENSE per dettagli.
