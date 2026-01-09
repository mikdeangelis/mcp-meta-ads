#!/usr/bin/env python3
"""
MCP Server for Meta Marketing API (Facebook/Instagram Ads).

Questo server fornisce accesso alle campagne pubblicitarie Facebook/Instagram
tramite la Meta Marketing API, con tool per analisi e gestione.
"""

import os
import json
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timedelta
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from pathlib import Path
from toon import encode as toon_encode, EncodeOptions

# Carica variabili d'ambiente dal file .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Inizializza il server MCP
mcp = FastMCP("meta_ads_mcp")

# Costanti
API_BASE_URL = "https://graph.facebook.com/v21.0"
CHARACTER_LIMIT = 25000
DEFAULT_TIMEOUT = 60.0


class ResponseFormat(str, Enum):
    """Formato di output per le risposte dei tool."""
    MARKDOWN = "markdown"
    JSON = "json"
    TOON = "toon"  # Token-optimized format (30-50% token savings)


class DatePreset(str, Enum):
    """Preset temporali disponibili per i report."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_3D = "last_3d"
    LAST_7D = "last_7d"
    LAST_14D = "last_14d"
    LAST_30D = "last_30d"
    LAST_90D = "last_90d"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LIFETIME = "lifetime"


class BreakdownType(str, Enum):
    """Tipi di breakdown disponibili per i report."""
    AGE = "age"
    GENDER = "gender"
    COUNTRY = "country"
    REGION = "region"
    PLACEMENT = "publisher_platform"
    DEVICE_PLATFORM = "device_platform"
    AGE_GENDER = "age,gender"


class CampaignObjective(str, Enum):
    """Obiettivi disponibili per le campagne Meta Ads."""
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"  # Notorietà
    OUTCOME_ENGAGEMENT = "OUTCOME_ENGAGEMENT"  # Interazione
    OUTCOME_LEADS = "OUTCOME_LEADS"  # Contatti
    OUTCOME_SALES = "OUTCOME_SALES"  # Vendite
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"  # Traffico
    OUTCOME_APP_PROMOTION = "OUTCOME_APP_PROMOTION"  # Promozione app


class CampaignStatus(str, Enum):
    """Stati possibili per una campagna."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class OptimizationGoal(str, Enum):
    """Obiettivi di ottimizzazione per gli ad set."""
    REACH = "REACH"  # Copertura
    IMPRESSIONS = "IMPRESSIONS"  # Impressioni
    LINK_CLICKS = "LINK_CLICKS"  # Clic sul link
    LANDING_PAGE_VIEWS = "LANDING_PAGE_VIEWS"  # Visualizzazioni landing page
    OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"  # Conversioni
    QUALITY_LEAD = "QUALITY_LEAD"  # Lead di qualità
    VALUE = "VALUE"  # Valore
    THRUPLAY = "THRUPLAY"  # Visualizzazioni video complete


class BillingEvent(str, Enum):
    """Eventi di fatturazione per gli ad set."""
    IMPRESSIONS = "IMPRESSIONS"  # Impressioni
    LINK_CLICKS = "LINK_CLICKS"  # Clic sul link
    THRUPLAY = "THRUPLAY"  # Visualizzazioni video complete


# Modelli Pydantic per validazione input

class ListAccountsInput(BaseModel):
    """Input per listare gli account pubblicitari."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    limit: Optional[int] = Field(
        default=25,
        description="Numero massimo di account da restituire (1-100)",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output: 'markdown' per lettura umana, 'json' per elaborazione"
    )


class ListCampaignsInput(BaseModel):
    """Input per listare le campagne di un account."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    account_id: str = Field(
        ...,
        description="ID dell'account pubblicitario (formato: 'act_123456789' o solo '123456789')",
        min_length=1
    )
    limit: Optional[int] = Field(
        default=25,
        description="Numero massimo di campagne da restituire (1-100)",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Assicura che l'account ID abbia il prefisso corretto."""
        if not v.startswith('act_'):
            return f'act_{v}'
        return v


class ListAdSetsInput(BaseModel):
    """Input per listare gli ad set di una campagna."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    campaign_id: str = Field(
        ...,
        description="ID della campagna (es. '120212345678901234')",
        min_length=1
    )
    limit: Optional[int] = Field(
        default=25,
        description="Numero massimo di ad set da restituire (1-100)",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class ListAdsInput(BaseModel):
    """Input per listare gli annunci di un ad set."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    adset_id: str = Field(
        ...,
        description="ID dell'ad set (es. '120212345678901234')",
        min_length=1
    )
    limit: Optional[int] = Field(
        default=25,
        description="Numero massimo di ads da restituire (1-100)",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class GetInsightsInput(BaseModel):
    """Input per ottenere metriche di performance."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    object_id: str = Field(
        ...,
        description="ID dell'oggetto (account, campagna, ad set o ad). Per account usa formato 'act_123456789'",
        min_length=1
    )
    level: Optional[str] = Field(
        default="account",
        description="Livello di aggregazione: 'account', 'campaign', 'adset', 'ad'"
    )
    date_preset: Optional[DatePreset] = Field(
        default=DatePreset.LAST_30D,
        description="Periodo temporale preset (es. 'last_7d', 'last_30d'). Ignorato se since/until sono specificati"
    )
    since: Optional[str] = Field(
        default=None,
        description="Data inizio custom range (formato: YYYY-MM-DD, es. '2025-01-01'). Richiede anche 'until'"
    )
    until: Optional[str] = Field(
        default=None,
        description="Data fine custom range (formato: YYYY-MM-DD, es. '2025-01-31'). Richiede anche 'since'"
    )
    time_increment: Optional[int] = Field(
        default=None,
        description="Granularità temporale in giorni (1=giornaliero, lasciare vuoto per totale periodo)",
        ge=1,
        le=90
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('until')
    @classmethod
    def validate_date_range(cls, v: Optional[str], info) -> Optional[str]:
        """Valida che since e until siano entrambi presenti o entrambi assenti."""
        since = info.data.get('since')
        if (since and not v) or (v and not since):
            raise ValueError("Se usi date personalizzate, devi specificare sia 'since' che 'until'")
        return v


class GetCreativeInput(BaseModel):
    """Input per ottenere i dettagli creativi di un annuncio."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    ad_id: str = Field(
        ...,
        description="ID dell'annuncio (es. '120212345678901234')",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class GenerateReportInput(BaseModel):
    """Input per generare report con breakdown demografici e geografici."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    object_id: str = Field(
        ...,
        description="ID dell'oggetto da analizzare (account, campagna, ad set o ad)",
        min_length=1
    )
    breakdowns: List[BreakdownType] = Field(
        default=[BreakdownType.AGE],
        description="Dimensioni di breakdown da applicare (max 4)",
        max_length=4
    )
    date_preset: Optional[DatePreset] = Field(
        default=DatePreset.LAST_30D,
        description="Periodo temporale preset. Ignorato se since/until sono specificati"
    )
    since: Optional[str] = Field(
        default=None,
        description="Data inizio custom range (formato: YYYY-MM-DD). Richiede anche 'until'"
    )
    until: Optional[str] = Field(
        default=None,
        description="Data fine custom range (formato: YYYY-MM-DD). Richiede anche 'since'"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('until')
    @classmethod
    def validate_date_range(cls, v: Optional[str], info) -> Optional[str]:
        """Valida che since e until siano entrambi presenti o entrambi assenti."""
        since = info.data.get('since')
        if (since and not v) or (v and not since):
            raise ValueError("Se usi date personalizzate, devi specificare sia 'since' che 'until'")
        return v


class AdSetStatus(str, Enum):
    """Stati possibili per un ad set."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class AdStatus(str, Enum):
    """Stati possibili per un annuncio."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class UpdateAdSetTargetingInput(BaseModel):
    """Input per aggiornare il targeting di un ad set."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    adset_id: str = Field(
        ...,
        description="ID dell'ad set da modificare",
        min_length=1
    )
    age_min: Optional[int] = Field(
        default=None,
        description="Età minima (18-65)",
        ge=18,
        le=65
    )
    age_max: Optional[int] = Field(
        default=None,
        description="Età massima (18-65)",
        ge=18,
        le=65
    )
    genders: Optional[List[int]] = Field(
        default=None,
        description="Lista generi: 1=uomini, 2=donne. Lasciare None per tutti"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('genders')
    @classmethod
    def validate_genders(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        """Valida che i valori di genere siano corretti."""
        if v is not None:
            for gender in v:
                if gender not in [1, 2]:
                    raise ValueError("I valori di genere devono essere 1 (uomini) o 2 (donne)")
        return v

    @field_validator('age_max')
    @classmethod
    def validate_age_range(cls, v: Optional[int], info) -> Optional[int]:
        """Valida che age_max sia >= age_min."""
        age_min = info.data.get('age_min')
        if age_min and v and v < age_min:
            raise ValueError("age_max deve essere maggiore o uguale ad age_min")
        return v


class UpdateAdSetBudgetInput(BaseModel):
    """Input per aggiornare il budget di un ad set."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    adset_id: str = Field(
        ...,
        description="ID dell'ad set da modificare",
        min_length=1
    )
    daily_budget: int = Field(
        ...,
        description="Budget giornaliero in centesimi (es. 1000 = €10.00)",
        ge=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class UpdateAdSetStatusInput(BaseModel):
    """Input per cambiare lo stato di un ad set."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    adset_id: str = Field(
        ...,
        description="ID dell'ad set da modificare",
        min_length=1
    )
    status: AdSetStatus = Field(
        ...,
        description="Nuovo stato: ACTIVE o PAUSED"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class UpdateAdStatusInput(BaseModel):
    """Input per cambiare lo stato di un annuncio."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    ad_id: str = Field(
        ...,
        description="ID dell'annuncio da modificare",
        min_length=1
    )
    status: AdStatus = Field(
        ...,
        description="Nuovo stato: ACTIVE o PAUSED"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class CreateCampaignInput(BaseModel):
    """Input per creare una nuova campagna."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    account_id: str = Field(
        ...,
        description="ID dell'account pubblicitario (formato: 'act_123456789' o solo '123456789')",
        min_length=1
    )
    name: str = Field(
        ...,
        description="Nome della campagna",
        min_length=1,
        max_length=400
    )
    objective: CampaignObjective = Field(
        ...,
        description="Obiettivo della campagna"
    )
    status: CampaignStatus = Field(
        default=CampaignStatus.PAUSED,
        description="Stato iniziale della campagna (default: PAUSED per sicurezza)"
    )
    daily_budget: Optional[int] = Field(
        default=None,
        description="Budget giornaliero in centesimi (es. 5000 = €50). Richiesto se non specifichi lifetime_budget",
        ge=100
    )
    lifetime_budget: Optional[int] = Field(
        default=None,
        description="Budget totale lifetime in centesimi (es. 10000 = €100). Richiesto se non specifichi daily_budget",
        ge=100
    )
    special_ad_categories: Optional[List[str]] = Field(
        default=["NONE"],
        description="Categorie speciali: CREDIT, EMPLOYMENT, HOUSING, ISSUES_ELECTIONS_POLITICS, ONLINE_GAMBLING_AND_GAMING, NONE (default)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Assicura che l'account ID abbia il prefisso corretto."""
        if not v.startswith('act_'):
            return f'act_{v}'
        return v

    @field_validator('daily_budget')
    @classmethod
    def validate_budgets(cls, v: Optional[int], info) -> Optional[int]:
        """Valida che almeno uno tra daily_budget e lifetime_budget sia specificato."""
        lifetime_budget = info.data.get('lifetime_budget')
        if v is None and lifetime_budget is None:
            raise ValueError("Devi specificare almeno uno tra daily_budget o lifetime_budget")
        if v is not None and lifetime_budget is not None:
            raise ValueError("Non puoi specificare sia daily_budget che lifetime_budget contemporaneamente")
        return v


class CreateAdSetInput(BaseModel):
    """Input per creare un nuovo ad set."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    campaign_id: str = Field(
        ...,
        description="ID della campagna a cui associare l'ad set",
        min_length=1
    )
    name: str = Field(
        ...,
        description="Nome dell'ad set",
        min_length=1,
        max_length=400
    )
    optimization_goal: OptimizationGoal = Field(
        ...,
        description="Obiettivo di ottimizzazione dell'ad set"
    )
    billing_event: BillingEvent = Field(
        ...,
        description="Evento di fatturazione"
    )
    bid_amount: Optional[int] = Field(
        default=None,
        description="Importo bid in centesimi. OBBLIGATORIO per optimization goals come LINK_CLICKS, LANDING_PAGE_VIEWS, ecc.",
        ge=1
    )
    daily_budget: Optional[int] = Field(
        default=None,
        description="Budget giornaliero in centesimi (es. 2000 = €20). NON usare se la campagna ha già un budget. Richiesto solo se la campagna non ha budget",
        ge=100
    )
    lifetime_budget: Optional[int] = Field(
        default=None,
        description="Budget lifetime in centesimi (es. 5000 = €50). Alternativa a daily_budget. NON usare se la campagna ha già un budget",
        ge=100
    )
    targeting: Dict[str, Any] = Field(
        ...,
        description="Oggetto targeting. OBBLIGATORI: geo_locations (paesi/regioni/città), targeting_automation.advantage_audience (0 o 1). OPZIONALI: age_min, age_max, genders"
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Data/ora di inizio (formato ISO 8601, es: '2025-01-15T00:00:00+0100'). Se non specificato, inizia subito quando attivato"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="Data/ora di fine (formato ISO 8601). Opzionale"
    )
    status: AdSetStatus = Field(
        default=AdSetStatus.PAUSED,
        description="Stato iniziale dell'ad set (default: PAUSED per sicurezza)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('targeting')
    @classmethod
    def validate_targeting(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Valida che il targeting abbia i campi obbligatori."""
        if 'geo_locations' not in v:
            raise ValueError("Il targeting deve includere 'geo_locations' con paesi, regioni o città")

        # Meta API richiede il flag advantage_audience (0 o 1)
        if 'targeting_automation' not in v:
            raise ValueError("Il targeting deve includere 'targeting_automation' con advantage_audience (0 o 1)")

        targeting_auto = v.get('targeting_automation', {})
        if 'advantage_audience' not in targeting_auto:
            raise ValueError("targeting_automation deve includere 'advantage_audience' (0=disabilitato, 1=abilitato)")

        return v

    @field_validator('daily_budget')
    @classmethod
    def validate_budgets(cls, v: Optional[int], info) -> Optional[int]:
        """Valida che non si specifichino sia daily che lifetime budget."""
        lifetime_budget = info.data.get('lifetime_budget')
        if v is not None and lifetime_budget is not None:
            raise ValueError("Non puoi specificare sia daily_budget che lifetime_budget contemporaneamente")
        return v


# Funzioni di utilità condivise

def _get_access_token() -> str:
    """Recupera il token di accesso dalle variabili d'ambiente."""
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "META_ACCESS_TOKEN non trovato. "
            "Imposta la variabile d'ambiente con il tuo access token Meta. "
            "Vedi README.md per istruzioni su come ottenerlo."
        )
    return token


async def _make_api_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Funzione riutilizzabile per tutte le chiamate API."""
    access_token = _get_access_token()

    if params is None:
        params = {}
    params["access_token"] = access_token

    async with httpx.AsyncClient() as client:
        url = f"{API_BASE_URL}/{endpoint}"

        # Meta Graph API accetta parametri come query string per tutte le operazioni
        response = await client.request(
            method,
            url,
            params=params,
            timeout=DEFAULT_TIMEOUT,
            **kwargs
        )
        response.raise_for_status()
        return response.json()


def _handle_api_error(e: Exception) -> str:
    """Gestione errori API consistente."""
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 400:
            try:
                error_data = e.response.json()
                error_obj = error_data.get("error", {})

                # Estrai tutti i campi utili
                error_msg = error_obj.get("message", "Richiesta non valida")
                error_code = error_obj.get("code", "")
                error_subcode = error_obj.get("error_subcode", "")
                error_user_msg = error_obj.get("error_user_msg", "")
                error_user_title = error_obj.get("error_user_title", "")
                fbtrace_id = error_obj.get("fbtrace_id", "")

                # Log completo per debug
                full_error = f"Errore: {error_msg}"
                if error_code:
                    full_error += f"\nCode: {error_code}"
                if error_subcode:
                    full_error += f"\nSubcode: {error_subcode}"
                if error_user_title:
                    full_error += f"\nTitolo: {error_user_title}"
                if error_user_msg:
                    full_error += f"\nDettagli: {error_user_msg}"
                if fbtrace_id:
                    full_error += f"\nTrace ID: {fbtrace_id}"
                return full_error
            except:
                return "Errore: Richiesta non valida. Controlla i parametri forniti."
        elif e.response.status_code == 401:
            return "Errore: Token di accesso non valido o scaduto. Genera un nuovo token e aggiorna META_ACCESS_TOKEN."
        elif e.response.status_code == 403:
            return "Errore: Permessi insufficienti. Verifica che il token abbia i permessi necessari (ads_management, ads_read)."
        elif e.response.status_code == 404:
            return "Errore: Risorsa non trovata. Verifica che l'ID sia corretto."
        elif e.response.status_code == 429:
            return "Errore: Rate limit raggiunto. Attendi qualche minuto prima di riprovare."
        elif e.response.status_code >= 500:
            return f"Errore: Problema temporaneo con i server Meta (status {e.response.status_code}). Riprova tra qualche minuto."
        return f"Errore API: status code {e.response.status_code}"
    elif isinstance(e, httpx.TimeoutException):
        return "Errore: Timeout della richiesta. Riprova o riduci la quantità di dati richiesti."
    elif isinstance(e, ValueError):
        return str(e)
    return f"Errore imprevisto: {type(e).__name__} - {str(e)}"


def _format_currency(amount: str, currency: str = "EUR") -> str:
    """Formatta un valore monetario da centesimi."""
    try:
        value = float(amount) / 100
        return f"{value:.2f} {currency}"
    except:
        return f"{amount} (raw)"


def _format_percentage(value: float) -> str:
    """Formatta una percentuale."""
    return f"{value:.2f}%"


def _check_truncation(content: str, data_count: int) -> str:
    """Verifica e gestisce il troncamento della risposta."""
    if len(content) > CHARACTER_LIMIT:
        truncated = content[:CHARACTER_LIMIT]
        truncated += f"\n\n⚠️ **Risposta troncata** - Mostrati primi {CHARACTER_LIMIT} caratteri su dati totali. "
        truncated += f"Usa parametri di filtro o paginazione per vedere più risultati."
        return truncated
    return content


def _format_as_toon(data: dict) -> str:
    """
    Formatta i dati in formato TOON (Token-Oriented Object Notation).

    TOON riduce i token del 30-50% rispetto a JSON, ottimale per dati tabellari.
    Usa indent=2 per leggibilità.

    Args:
        data: Dizionario da convertire in TOON

    Returns:
        Stringa in formato TOON
    """
    try:
        return toon_encode(data, EncodeOptions(indent=2))
    except Exception as e:
        # Fallback a JSON se TOON encoding fallisce
        return json.dumps(data, indent=2, ensure_ascii=False)


# Implementazione tool

@mcp.tool(
    name="meta_ads_list_accounts",
    annotations={
        "title": "Lista Account Pubblicitari Meta",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_list_accounts(params: ListAccountsInput) -> str:
    """
    Elenca tutti gli account pubblicitari Meta a cui l'utente ha accesso.

    Questo tool recupera la lista degli ad account disponibili per l'access token fornito,
    mostrando informazioni chiave come nome, ID, valuta e stato dell'account.

    Args:
        params (ListAccountsInput): Parametri validati contenenti:
            - limit (int): Numero massimo di account da restituire (default: 25, range: 1-100)
            - response_format (ResponseFormat): Formato output ('markdown' o 'json')

    Returns:
        str: Lista formattata degli account con le seguenti informazioni per ogni account:
            - ID (formato act_XXXXX)
            - Nome dell'account
            - Valuta
            - Stato (attivo/disabilitato)
            - Timezone

        Formato Markdown (default):
        # Account Pubblicitari Meta
        Trovati X account

        ## Nome Account (act_123456789)
        - **Valuta**: EUR
        - **Stato**: ACTIVE
        - **Timezone**: Europe/Rome

        Formato JSON:
        {
            "total": int,
            "count": int,
            "accounts": [
                {
                    "id": "act_123456789",
                    "name": "Nome Account",
                    "currency": "EUR",
                    "account_status": 1,
                    "timezone_name": "Europe/Rome"
                }
            ]
        }

    Esempi d'uso:
        - "Mostrami tutti i miei account pubblicitari Meta"
        - "Quali account Facebook Ads ho disponibili?"
        - "Lista i miei account con il budget disponibile"

    Note:
        - Richiede permesso ads_read
        - L'ID ritornato (act_XXXXX) deve essere usato per le chiamate successive
        - Lo stato può essere: ACTIVE (1), DISABLED (2), UNSETTLED (3), ecc.
    """
    try:
        data = await _make_api_request(
            "me/adaccounts",
            params={
                "fields": "id,name,currency,account_status,timezone_name,business",
                "limit": params.limit
            }
        )

        accounts = data.get("data", [])

        if not accounts:
            return "Nessun account pubblicitario trovato. Verifica i permessi del token."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Account Pubblicitari Meta\n"]
            lines.append(f"Trovati {len(accounts)} account\n")

            for acc in accounts:
                status_map = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED"}
                status = status_map.get(acc.get("account_status", 0), "UNKNOWN")

                lines.append(f"## {acc['name']} ({acc['id']})")
                lines.append(f"- **Valuta**: {acc['currency']}")
                lines.append(f"- **Stato**: {status}")
                lines.append(f"- **Timezone**: {acc.get('timezone_name', 'N/A')}")
                if 'business' in acc:
                    lines.append(f"- **Business**: {acc['business'].get('name', 'N/A')}")
                lines.append("")

            content = "\n".join(lines)
            return _check_truncation(content, len(accounts))

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "total": len(accounts),
                "count": len(accounts),
                "accounts": accounts
            }
            return _format_as_toon(result)
        else:
            result = {
                "total": len(accounts),
                "count": len(accounts),
                "accounts": accounts
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_list_campaigns",
    annotations={
        "title": "Lista Campagne Pubblicitarie",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_list_campaigns(params: ListCampaignsInput) -> str:
    """
    Elenca tutte le campagne pubblicitarie di un account Meta.

    Recupera la lista completa delle campagne per un account specificato, con dettagli
    su obiettivo, stato, budget e scheduling.

    Args:
        params (ListCampaignsInput): Parametri validati contenenti:
            - account_id (str): ID account (formato 'act_123456789' o '123456789')
            - limit (int): Numero massimo di campagne (default: 25, range: 1-100)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Lista campagne con:
            - ID e nome campagna
            - Obiettivo pubblicitario (es. CONVERSIONS, TRAFFIC, BRAND_AWARENESS)
            - Stato (ACTIVE, PAUSED, DELETED, ARCHIVED)
            - Budget giornaliero o lifetime
            - Date inizio/fine (se programmate)
            - Numero di ad set associati

    Esempi d'uso:
        - "Mostrami tutte le campagne attive per l'account act_123456"
        - "Quali campagne ho in corso?"
        - "Lista le campagne con budget e obiettivi"

    Note:
        - Lo stato può essere: ACTIVE, PAUSED, DELETED, ARCHIVED
        - Il budget è in centesimi (es. 5000 = 50.00 EUR)
        - L'obiettivo indica lo scopo della campagna (conversioni, traffico, ecc.)
    """
    try:
        data = await _make_api_request(
            f"{params.account_id}/campaigns",
            params={
                "fields": "id,name,objective,status,daily_budget,lifetime_budget,start_time,stop_time",
                "limit": params.limit
            }
        )

        campaigns = data.get("data", [])

        if not campaigns:
            return f"Nessuna campagna trovata per l'account {params.account_id}."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Campagne Pubblicitarie\n"]
            lines.append(f"Account: {params.account_id}")
            lines.append(f"Trovate {len(campaigns)} campagne\n")

            for camp in campaigns:
                lines.append(f"## {camp['name']} ({camp['id']})")
                lines.append(f"- **Obiettivo**: {camp.get('objective', 'N/A')}")
                lines.append(f"- **Stato**: {camp.get('status', 'N/A')}")

                if 'daily_budget' in camp:
                    budget = _format_currency(camp['daily_budget'])
                    lines.append(f"- **Budget giornaliero**: {budget}")
                elif 'lifetime_budget' in camp:
                    budget = _format_currency(camp['lifetime_budget'])
                    lines.append(f"- **Budget lifetime**: {budget}")

                if 'start_time' in camp:
                    lines.append(f"- **Inizio**: {camp['start_time']}")
                if 'stop_time' in camp:
                    lines.append(f"- **Fine**: {camp['stop_time']}")

                lines.append("")

            content = "\n".join(lines)
            return _check_truncation(content, len(campaigns))

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "account_id": params.account_id,
                "total": len(campaigns),
                "count": len(campaigns),
                "campaigns": campaigns
            }
            return _format_as_toon(result)
        else:
            result = {
                "account_id": params.account_id,
                "total": len(campaigns),
                "count": len(campaigns),
                "campaigns": campaigns
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_list_adsets",
    annotations={
        "title": "Lista Ad Set di una Campagna",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_list_adsets(params: ListAdSetsInput) -> str:
    """
    Elenca tutti gli ad set di una campagna specifica.

    Gli ad set definiscono budget, scheduling, targeting e ottimizzazione
    per gruppi di annunci all'interno di una campagna.

    Args:
        params (ListAdSetsInput): Parametri validati contenenti:
            - campaign_id (str): ID della campagna
            - limit (int): Numero massimo di ad set (default: 25)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Lista ad set con:
            - ID e nome
            - Stato (ACTIVE, PAUSED, ecc.)
            - Budget giornaliero o lifetime
            - Ottimizzazione e strategia di bid
            - Eventi di ottimizzazione
            - Date scheduling

    Esempi d'uso:
        - "Mostrami gli ad set della campagna 123456789"
        - "Quali ad set sono attivi in questa campagna?"
        - "Lista ad set con budget e targeting"
    """
    try:
        data = await _make_api_request(
            f"{params.campaign_id}/adsets",
            params={
                "fields": "id,name,status,daily_budget,lifetime_budget,optimization_goal,billing_event,start_time,end_time",
                "limit": params.limit
            }
        )

        adsets = data.get("data", [])

        if not adsets:
            return f"Nessun ad set trovato per la campagna {params.campaign_id}."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Ad Set\n"]
            lines.append(f"Campagna: {params.campaign_id}")
            lines.append(f"Trovati {len(adsets)} ad set\n")

            for adset in adsets:
                lines.append(f"## {adset['name']} ({adset['id']})")
                lines.append(f"- **Stato**: {adset.get('status', 'N/A')}")

                if 'daily_budget' in adset:
                    budget = _format_currency(adset['daily_budget'])
                    lines.append(f"- **Budget giornaliero**: {budget}")
                elif 'lifetime_budget' in adset:
                    budget = _format_currency(adset['lifetime_budget'])
                    lines.append(f"- **Budget lifetime**: {budget}")

                if 'optimization_goal' in adset:
                    lines.append(f"- **Ottimizzazione**: {adset['optimization_goal']}")
                if 'billing_event' in adset:
                    lines.append(f"- **Billing**: {adset['billing_event']}")

                if 'start_time' in adset:
                    lines.append(f"- **Inizio**: {adset['start_time']}")
                if 'end_time' in adset:
                    lines.append(f"- **Fine**: {adset['end_time']}")

                lines.append("")

            content = "\n".join(lines)
            return _check_truncation(content, len(adsets))

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "campaign_id": params.campaign_id,
                "total": len(adsets),
                "count": len(adsets),
                "adsets": adsets
            }
            return _format_as_toon(result)
        else:
            result = {
                "campaign_id": params.campaign_id,
                "total": len(adsets),
                "count": len(adsets),
                "adsets": adsets
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_list_ads",
    annotations={
        "title": "Lista Annunci di un Ad Set",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_list_ads(params: ListAdsInput) -> str:
    """
    Elenca tutti gli annunci di un ad set specifico.

    Gli annunci (ads) sono il livello più granulare della struttura pubblicitaria
    e contengono il creative effettivo mostrato agli utenti.

    Args:
        params (ListAdsInput): Parametri validati contenenti:
            - adset_id (str): ID dell'ad set
            - limit (int): Numero massimo di ads (default: 25)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Lista annunci con:
            - ID e nome
            - Stato
            - ID creative associato
            - Informazioni base sul targeting
            - Link al creative completo

    Esempi d'uso:
        - "Mostrami gli annunci dell'ad set 123456789"
        - "Quali ads sono attivi in questo ad set?"
        - "Lista tutti gli annunci con i loro creative"

    Note:
        - Per dettagli completi sul creative, usa meta_ads_get_creative
    """
    try:
        data = await _make_api_request(
            f"{params.adset_id}/ads",
            params={
                "fields": "id,name,status,creative{id,name}",
                "limit": params.limit
            }
        )

        ads = data.get("data", [])

        if not ads:
            return f"Nessun annuncio trovato per l'ad set {params.adset_id}."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Annunci\n"]
            lines.append(f"Ad Set: {params.adset_id}")
            lines.append(f"Trovati {len(ads)} annunci\n")

            for ad in ads:
                lines.append(f"## {ad['name']} ({ad['id']})")
                lines.append(f"- **Stato**: {ad.get('status', 'N/A')}")

                if 'creative' in ad:
                    creative = ad['creative']
                    lines.append(f"- **Creative ID**: {creative.get('id', 'N/A')}")
                    lines.append(f"- **Creative Nome**: {creative.get('name', 'N/A')}")

                lines.append(f"- *Usa meta_ads_get_creative con ID {ad['id']} per dettagli completi*")
                lines.append("")

            content = "\n".join(lines)
            return _check_truncation(content, len(ads))

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "adset_id": params.adset_id,
                "total": len(ads),
                "count": len(ads),
                "ads": ads
            }
            return _format_as_toon(result)
        else:
            result = {
                "adset_id": params.adset_id,
                "total": len(ads),
                "count": len(ads),
                "ads": ads
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_get_insights",
    annotations={
        "title": "Ottieni Metriche Performance",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_get_insights(params: GetInsightsInput) -> str:
    """
    Recupera metriche di performance dettagliate per account, campagne, ad set o singoli ads.

    Fornisce accesso completo all'Insights API di Meta con metriche chiave come
    impressions, clicks, spend, conversions, CPC, CTR, ROAS e molto altro.

    Args:
        params (GetInsightsInput): Parametri validati contenenti:
            - object_id (str): ID dell'oggetto da analizzare
            - level (str): Livello aggregazione ('account', 'campaign', 'adset', 'ad')
            - date_preset (DatePreset): Periodo temporale preset (es. 'last_30d', 'this_month')
            - since (str): Data inizio custom (formato YYYY-MM-DD, es. '2025-01-01')
            - until (str): Data fine custom (formato YYYY-MM-DD, es. '2025-01-31')
            - time_increment (int): Granularità giorni (1=daily, vuoto=totale periodo)
            - response_format (ResponseFormat): Formato output

        Note: Se specifichi 'since' e 'until', il 'date_preset' viene ignorato.

    Returns:
        str: Metriche complete con:
            - Impressions (visualizzazioni)
            - Clicks (clic ricevuti)
            - Spend (spesa in valuta account)
            - CPM (costo per mille impressioni)
            - CPC (costo per clic)
            - CTR (click-through rate %)
            - Reach (utenti unici raggiunti)
            - Frequency (frequenza media)
            - Conversions (azioni completate)
            - Cost per result (costo per conversione)
            - ROAS (return on ad spend, se disponibile)

        Se time_increment è specificato, restituisce metriche aggregate per periodo.

    Esempi d'uso:
        - "Mostrami le performance dell'account nell'ultimo mese"
        - "Quanto ho speso questa settimana sulla campagna 123?"
        - "Qual è il CTR degli ultimi 7 giorni per questo ad set?"
        - "Dammi i dati giornalieri dell'ultima settimana"
        - "Mostrami le metriche dal 1 gennaio al 31 gennaio 2025"
        - "Analizza le performance dal 2024-12-01 al 2024-12-31"

    Note:
        - I valori monetari sono in centesimi
        - Le conversions dipendono dal pixel/events configurati
        - ROAS richiede impostazione valore conversioni
        - Alcune metriche potrebbero non essere disponibili per tutti gli obiettivi
        - Range massimo: 37 mesi (con alcune limitazioni per breakdown)
    """
    try:
        request_params = {
            "fields": "impressions,clicks,spend,cpm,cpc,ctr,reach,frequency,actions,cost_per_action_type,action_values",
            "level": params.level
        }

        # Usa date personalizzate se fornite, altrimenti usa preset
        if params.since and params.until:
            request_params["time_range"] = json.dumps({
                "since": params.since,
                "until": params.until
            })
            date_info = f"{params.since} - {params.until}"
        else:
            request_params["date_preset"] = params.date_preset.value
            date_info = params.date_preset.value

        if params.time_increment:
            request_params["time_increment"] = params.time_increment

        data = await _make_api_request(
            f"{params.object_id}/insights",
            params=request_params
        )

        insights = data.get("data", [])

        if not insights:
            return f"Nessun dato insight disponibile per {params.object_id} nel periodo selezionato."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Metriche Performance\n"]
            lines.append(f"Oggetto: {params.object_id}")
            lines.append(f"Periodo: {date_info}")
            lines.append(f"Livello: {params.level}\n")

            for idx, insight in enumerate(insights, 1):
                if params.time_increment:
                    period = f"{insight.get('date_start', 'N/A')} - {insight.get('date_stop', 'N/A')}"
                    lines.append(f"## Periodo {idx}: {period}")
                else:
                    lines.append(f"## Metriche Totali")

                lines.append(f"- **Impressions**: {int(insight.get('impressions', '0')):,}")
                lines.append(f"- **Clicks**: {int(insight.get('clicks', '0')):,}")
                lines.append(f"- **Spend**: {_format_currency(insight.get('spend', '0'))}")
                lines.append(f"- **CPM**: {_format_currency(insight.get('cpm', '0'))}")
                lines.append(f"- **CPC**: {_format_currency(insight.get('cpc', '0'))}")

                ctr = insight.get('ctr', 0)
                lines.append(f"- **CTR**: {_format_percentage(float(ctr))}")

                lines.append(f"- **Reach**: {int(insight.get('reach', '0')):,}")
                lines.append(f"- **Frequency**: {insight.get('frequency', '0')}")

                # Conversioni
                if 'actions' in insight:
                    lines.append("- **Conversioni**:")
                    for action in insight['actions'][:5]:  # Primi 5 tipi
                        action_type = action.get('action_type', 'unknown')
                        value = action.get('value', '0')
                        lines.append(f"  - {action_type}: {value}")

                lines.append("")

            content = "\n".join(lines)
            return _check_truncation(content, len(insights))

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "object_id": params.object_id,
                "level": params.level,
                "period": date_info,
                "total": len(insights),
                "insights": insights
            }
            return _format_as_toon(result)
        else:
            result = {
                "object_id": params.object_id,
                "level": params.level,
                "period": date_info,
                "total": len(insights),
                "insights": insights
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_get_creative",
    annotations={
        "title": "Ottieni Dettagli Creative Annuncio",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_get_creative(params: GetCreativeInput) -> str:
    """
    Recupera i dettagli completi del creative di un annuncio specifico.

    Il creative contiene tutti gli elementi visuali e testuali dell'annuncio:
    testi, immagini, video, link, call-to-action e configurazione placement.

    Args:
        params (GetCreativeInput): Parametri validati contenenti:
            - ad_id (str): ID dell'annuncio
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Dettagli creative completi:
            - ID creative
            - Nome creative
            - Titolo annuncio
            - Body text (testo principale)
            - Descrizione/caption
            - Call to action type (es. LEARN_MORE, SHOP_NOW)
            - Link URL
            - Image hash/URL (per annunci immagine)
            - Video ID (per annunci video)
            - Page ID e Instagram actor ID
            - Object story spec (configurazione placement)
            - Asset feed spec (per annunci dinamici)

    Esempi d'uso:
        - "Mostrami il creative dell'annuncio 123456789"
        - "Quali testi e immagini usa questo ad?"
        - "Dammi il link e la CTA di questo annuncio"

    Note:
        - La struttura dati varia in base al formato annuncio (immagine, video, carousel, ecc.)
        - Per annunci dinamici, guarda asset_feed_spec
        - Le immagini sono identificate da hash, non URL diretti
    """
    try:
        # Prima ottieni l'ad per ricavare il creative ID
        ad_data = await _make_api_request(
            params.ad_id,
            params={"fields": "creative{id,name,title,body,image_url,link_url,call_to_action_type,object_story_spec,asset_feed_spec}"}
        )

        if 'creative' not in ad_data:
            return f"Nessun creative trovato per l'annuncio {params.ad_id}."

        creative = ad_data['creative']

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Dettagli Creative\n"]
            lines.append(f"Annuncio ID: {params.ad_id}")
            lines.append(f"Creative ID: {creative.get('id', 'N/A')}\n")

            if 'name' in creative:
                lines.append(f"## {creative['name']}\n")

            if 'title' in creative:
                lines.append(f"### Titolo")
                lines.append(f"{creative['title']}\n")

            if 'body' in creative:
                lines.append(f"### Body Text")
                lines.append(f"{creative['body']}\n")

            if 'link_url' in creative:
                lines.append(f"**Link**: {creative['link_url']}")

            if 'call_to_action_type' in creative:
                lines.append(f"**Call to Action**: {creative['call_to_action_type']}")

            if 'image_url' in creative:
                lines.append(f"**Immagine**: {creative['image_url']}")

            # Object story spec
            if 'object_story_spec' in creative:
                lines.append("\n### Configurazione Placement")
                spec = creative['object_story_spec']
                if 'page_id' in spec:
                    lines.append(f"- **Page ID**: {spec['page_id']}")
                if 'instagram_actor_id' in spec:
                    lines.append(f"- **Instagram Actor ID**: {spec['instagram_actor_id']}")
                if 'link_data' in spec:
                    link_data = spec['link_data']
                    if 'link' in link_data:
                        lines.append(f"- **Link**: {link_data['link']}")
                    if 'message' in link_data:
                        lines.append(f"- **Messaggio**: {link_data['message']}")

            # Asset feed (per annunci dinamici)
            if 'asset_feed_spec' in creative:
                lines.append("\n### Asset Feed (Annuncio Dinamico)")
                lines.append("*Configurazione per annunci dinamici presente*")

            content = "\n".join(lines)
            return content

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "ad_id": params.ad_id,
                "creative": creative
            }
            return _format_as_toon(result)
        else:
            result = {
                "ad_id": params.ad_id,
                "creative": creative
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_generate_report",
    annotations={
        "title": "Genera Report con Breakdown Demografici",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def meta_ads_generate_report(params: GenerateReportInput) -> str:
    """
    Genera report avanzati con breakdown per età, genere, paese, regione e placement.

    Questo tool fornisce analisi approfondite segmentando le performance per diverse
    dimensioni demografiche e geografiche, permettendo di identificare il pubblico
    più performante e ottimizzare il targeting.

    Args:
        params (GenerateReportInput): Parametri validati contenenti:
            - object_id (str): ID oggetto da analizzare (account, campagna, ad set, ad)
            - breakdowns (List[BreakdownType]): Dimensioni di segmentazione (max 4):
                * 'age': Fasce d'età (18-24, 25-34, 35-44, 45-54, 55-64, 65+)
                * 'gender': Genere (male, female, unknown)
                * 'country': Paese (codice ISO, es. IT, US, GB)
                * 'region': Regione geografica
                * 'publisher_platform': Placement (Facebook, Instagram, Messenger, Audience Network)
                * 'device_platform': Piattaforma device (mobile, desktop)
                * 'age,gender': Combinazione età+genere
            - date_preset (DatePreset): Periodo analisi preset (default: last_30d)
            - since (str): Data inizio custom (formato YYYY-MM-DD)
            - until (str): Data fine custom (formato YYYY-MM-DD)
            - response_format (ResponseFormat): Formato output

        Note: Se specifichi 'since' e 'until', il 'date_preset' viene ignorato.

    Returns:
        str: Report segmentato con metriche per ogni combinazione di breakdown:
            - Impressions per segmento
            - Clicks per segmento
            - Spend per segmento
            - CTR per segmento
            - CPC per segmento
            - Conversioni per segmento (se disponibili)

        Il report evidenzia i segmenti più performanti e quelli meno efficaci.

    Esempi d'uso:
        - "Mostrami le performance per fascia d'età e genere negli ultimi 30 giorni"
        - "Quale paese ha il CTR migliore?"
        - "Come performano gli annunci su Instagram vs Facebook?"
        - "Analizza la distribuzione per età dell'ultima settimana"
        - "Report per genere dal 1 dicembre al 31 dicembre 2024"
        - "Breakdown per paese dal 2025-01-01 al 2025-01-31"

    Note:
        - I breakdown multipli moltiplicano le righe (es. 6 età x 2 generi = 12 segmenti)
        - Alcuni breakdown non sono compatibili tra loro
        - Dati limitati a 394 giorni per breakdown demografici con Reach
        - Segmenti con pochi dati potrebbero non essere mostrati per privacy
    """
    try:
        breakdown_str = ",".join([b.value for b in params.breakdowns])

        request_params = {
            "fields": "impressions,clicks,spend,cpc,ctr,reach,actions,cost_per_action_type",
            "breakdowns": breakdown_str
        }

        # Usa date personalizzate se fornite, altrimenti usa preset
        if params.since and params.until:
            request_params["time_range"] = json.dumps({
                "since": params.since,
                "until": params.until
            })
            date_info = f"{params.since} - {params.until}"
        else:
            request_params["date_preset"] = params.date_preset.value
            date_info = params.date_preset.value

        data = await _make_api_request(
            f"{params.object_id}/insights",
            params=request_params
        )

        insights = data.get("data", [])

        if not insights:
            return f"Nessun dato disponibile per i breakdown richiesti nel periodo {date_info}."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# Report con Breakdown\n"]
            lines.append(f"Oggetto: {params.object_id}")
            lines.append(f"Periodo: {date_info}")
            lines.append(f"Breakdown: {breakdown_str}\n")
            lines.append(f"Totale segmenti: {len(insights)}\n")

            # Raggruppa e mostra top performers
            sorted_insights = sorted(insights, key=lambda x: int(x.get('clicks', 0)), reverse=True)

            for idx, insight in enumerate(sorted_insights[:20], 1):  # Top 20
                # Costruisci il titolo del segmento
                segment_parts = []
                if 'age' in insight:
                    segment_parts.append(f"Età: {insight['age']}")
                if 'gender' in insight:
                    gender_map = {'male': 'Uomo', 'female': 'Donna', 'unknown': 'Non specificato'}
                    segment_parts.append(f"Genere: {gender_map.get(insight['gender'], insight['gender'])}")
                if 'country' in insight:
                    segment_parts.append(f"Paese: {insight['country']}")
                if 'region' in insight:
                    segment_parts.append(f"Regione: {insight['region']}")
                if 'publisher_platform' in insight:
                    segment_parts.append(f"Platform: {insight['publisher_platform']}")
                if 'device_platform' in insight:
                    segment_parts.append(f"Device: {insight['device_platform']}")

                segment_title = " | ".join(segment_parts) if segment_parts else f"Segmento {idx}"
                lines.append(f"## {idx}. {segment_title}")

                lines.append(f"- **Impressions**: {int(insight.get('impressions', '0')):,}")
                lines.append(f"- **Clicks**: {int(insight.get('clicks', '0')):,}")
                lines.append(f"- **Spend**: {_format_currency(insight.get('spend', '0'))}")

                ctr = float(insight.get('ctr', 0))
                lines.append(f"- **CTR**: {_format_percentage(ctr)}")
                lines.append(f"- **CPC**: {_format_currency(insight.get('cpc', '0'))}")

                if 'reach' in insight:
                    lines.append(f"- **Reach**: {int(insight['reach']):,}")

                if 'actions' in insight:
                    total_actions = sum(int(a.get('value', 0)) for a in insight['actions'])
                    lines.append(f"- **Conversioni totali**: {total_actions}")

                lines.append("")

            if len(sorted_insights) > 20:
                lines.append(f"\n*Mostrati i top 20 segmenti su {len(insights)} totali*")
                lines.append("*Usa filtri o parametri diversi per vedere altri segmenti*\n")

            content = "\n".join(lines)
            return _check_truncation(content, len(insights))

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "object_id": params.object_id,
                "breakdowns": breakdown_str,
                "period": date_info,
                "total_segments": len(insights),
                "insights": insights
            }
            return _format_as_toon(result)
        else:
            result = {
                "object_id": params.object_id,
                "breakdowns": breakdown_str,
                "period": date_info,
                "total_segments": len(insights),
                "insights": insights
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_update_adset_targeting",
    annotations={
        "title": "Aggiorna Targeting Ad Set",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def meta_ads_update_adset_targeting(params: UpdateAdSetTargetingInput) -> str:
    """
    Aggiorna il targeting demografico di un ad set (età e genere).

    Questo tool permette di modificare le impostazioni di età minima/massima
    e genere del pubblico target di un ad set esistente.

    Args:
        params (UpdateAdSetTargetingInput): Parametri validati contenenti:
            - adset_id (str): ID dell'ad set da modificare
            - age_min (Optional[int]): Età minima (18-65)
            - age_max (Optional[int]): Età massima (18-65)
            - genders (Optional[List[int]]): Lista generi (1=uomini, 2=donne)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Conferma delle modifiche applicate con dettagli del nuovo targeting

    Esempi d'uso:
        - "Imposta età 25-44 per ad set 123456789"
        - "Cambia targeting a solo donne 25-54 anni"
        - "Restringe ad set a uomini 35-65 anni"

    Note:
        - Se non specifichi age_min o age_max, mantiene il valore esistente
        - Se non specifichi genders, targettizza tutti i generi
        - Per solo donne: genders=[2]
        - Per solo uomini: genders=[1]
        - Per tutti i generi: genders=None o non specificare
    """
    try:
        # Prima recupera il targeting attuale
        current_data = await _make_api_request(
            params.adset_id,
            params={"fields": "name,targeting"}
        )

        current_targeting = current_data.get('targeting', {})
        adset_name = current_data.get('name', params.adset_id)

        # Prepara il nuovo targeting (mantiene le altre impostazioni)
        updated_targeting = current_targeting.copy()

        # Aggiorna età se specificata
        if params.age_min is not None:
            updated_targeting['age_min'] = params.age_min
        if params.age_max is not None:
            updated_targeting['age_max'] = params.age_max

        # Aggiorna genere se specificato
        if params.genders is not None:
            updated_targeting['genders'] = params.genders
        elif 'genders' in updated_targeting:
            # Se genders non è specificato, rimuovilo per targettizzare tutti
            del updated_targeting['genders']

        # Esegui l'aggiornamento
        update_data = await _make_api_request(
            params.adset_id,
            method="POST",
            params={
                "targeting": json.dumps(updated_targeting)
            }
        )

        if not update_data.get('success'):
            return f"Errore nell'aggiornamento dell'ad set {params.adset_id}"

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Targeting Ad Set Aggiornato\n"]
            lines.append(f"**Ad Set**: {adset_name}")
            lines.append(f"**ID**: {params.adset_id}\n")

            lines.append("## Nuovo Targeting Demografico\n")

            # Età
            age_min = updated_targeting.get('age_min', 18)
            age_max = updated_targeting.get('age_max', 65)
            lines.append(f"- **Età**: {age_min}-{age_max} anni")

            # Genere
            genders = updated_targeting.get('genders')
            if genders:
                gender_map = {1: 'Uomini', 2: 'Donne'}
                gender_str = ', '.join([gender_map.get(g, str(g)) for g in genders])
                lines.append(f"- **Genere**: {gender_str}")
            else:
                lines.append(f"- **Genere**: Tutti")

            # Mostra cosa è cambiato
            changes = []
            if params.age_min is not None or params.age_max is not None:
                old_age_min = current_targeting.get('age_min', 18)
                old_age_max = current_targeting.get('age_max', 65)
                if old_age_min != age_min or old_age_max != age_max:
                    changes.append(f"Età cambiata da {old_age_min}-{old_age_max} a {age_min}-{age_max}")

            if params.genders is not None:
                old_genders = current_targeting.get('genders')
                if old_genders != genders:
                    changes.append("Filtro genere aggiornato")

            if changes:
                lines.append("\n## Modifiche Applicate\n")
                for change in changes:
                    lines.append(f"✓ {change}")

            lines.append("\n*Le altre impostazioni di targeting (geografia, interessi, ecc.) sono rimaste invariate*")

            return "\n".join(lines)

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "success": True,
                "adset_id": params.adset_id,
                "adset_name": adset_name,
                "updated_targeting": updated_targeting
            }
            return _format_as_toon(result)
        else:
            result = {
                "success": True,
                "adset_id": params.adset_id,
                "adset_name": adset_name,
                "updated_targeting": updated_targeting
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_update_adset_budget",
    annotations={
        "title": "Aggiorna Budget Ad Set",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def meta_ads_update_adset_budget(params: UpdateAdSetBudgetInput) -> str:
    """
    Aggiorna il budget giornaliero di un ad set.

    Questo tool permette di modificare il budget giornaliero allocato
    a un ad set esistente.

    Args:
        params (UpdateAdSetBudgetInput): Parametri validati contenenti:
            - adset_id (str): ID dell'ad set da modificare
            - daily_budget (int): Nuovo budget giornaliero in centesimi (es. 1000 = €10)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Conferma della modifica con vecchio e nuovo budget

    Esempi d'uso:
        - "Imposta budget €15/giorno per ad set 123456789" (daily_budget=1500)
        - "Aumenta budget a €25 al giorno" (daily_budget=2500)
        - "Riduci budget a €5 giornalieri" (daily_budget=500)

    Note:
        - Il budget è in centesimi: 1000 = €10.00
        - Budget minimo: €1.00 (100 centesimi)
        - La modifica ha effetto immediato
        - Non cambia il lifetime_budget se configurato
    """
    try:
        # Prima recupera i dati attuali
        current_data = await _make_api_request(
            params.adset_id,
            params={"fields": "name,daily_budget,status"}
        )

        adset_name = current_data.get('name', params.adset_id)
        old_budget = int(current_data.get('daily_budget', 0))
        status = current_data.get('status', 'UNKNOWN')

        # Esegui l'aggiornamento
        update_data = await _make_api_request(
            params.adset_id,
            method="POST",
            params={
                "daily_budget": params.daily_budget
            }
        )

        if not update_data.get('success'):
            return f"Errore nell'aggiornamento del budget per ad set {params.adset_id}"

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Budget Ad Set Aggiornato\n"]
            lines.append(f"**Ad Set**: {adset_name}")
            lines.append(f"**ID**: {params.adset_id}")
            lines.append(f"**Status**: {status}\n")

            lines.append("## Modifica Budget\n")
            lines.append(f"- **Budget Precedente**: €{old_budget/100:.2f}/giorno")
            lines.append(f"- **Nuovo Budget**: €{params.daily_budget/100:.2f}/giorno")

            diff = params.daily_budget - old_budget
            diff_pct = (diff / old_budget * 100) if old_budget > 0 else 0

            if diff > 0:
                lines.append(f"- **Variazione**: +€{diff/100:.2f} (+{diff_pct:.1f}%) 📈")
            elif diff < 0:
                lines.append(f"- **Variazione**: €{diff/100:.2f} ({diff_pct:.1f}%) 📉")
            else:
                lines.append(f"- **Variazione**: Nessuna modifica")

            lines.append("\n*Il nuovo budget sarà applicato a partire dalla prossima auction*")

            return "\n".join(lines)

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "success": True,
                "adset_id": params.adset_id,
                "adset_name": adset_name,
                "old_budget_cents": old_budget,
                "new_budget_cents": params.daily_budget,
                "difference_cents": params.daily_budget - old_budget
            }
            return _format_as_toon(result)
        else:
            result = {
                "success": True,
                "adset_id": params.adset_id,
                "adset_name": adset_name,
                "old_budget_cents": old_budget,
                "new_budget_cents": params.daily_budget,
                "difference_cents": params.daily_budget - old_budget
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_update_adset_status",
    annotations={
        "title": "Cambia Stato Ad Set",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def meta_ads_update_adset_status(params: UpdateAdSetStatusInput) -> str:
    """
    Attiva o mette in pausa un ad set.

    Questo tool permette di cambiare lo stato di un ad set tra
    ACTIVE (attivo, mostra annunci) e PAUSED (in pausa, non mostra annunci).

    Args:
        params (UpdateAdSetStatusInput): Parametri validati contenenti:
            - adset_id (str): ID dell'ad set da modificare
            - status (AdSetStatus): Nuovo stato (ACTIVE o PAUSED)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Conferma del cambio di stato

    Esempi d'uso:
        - "Attiva ad set 123456789" (status=ACTIVE)
        - "Metti in pausa ad set 987654321" (status=PAUSED)
        - "Pausa tutti gli ad set della campagna" (chiamare per ogni ad set)

    Note:
        - Il cambio stato ha effetto immediato
        - Ad set PAUSED non consumano budget
        - Ad set ACTIVE iniziano subito a competere nelle auction
        - La campagna deve essere attiva perché l'ad set possa essere attivo
    """
    try:
        # Prima recupera i dati attuali
        current_data = await _make_api_request(
            params.adset_id,
            params={"fields": "name,status,daily_budget"}
        )

        adset_name = current_data.get('name', params.adset_id)
        old_status = current_data.get('status', 'UNKNOWN')
        budget = int(current_data.get('daily_budget', 0))

        # Se lo stato è già quello richiesto, comunica che non serve modificare
        if old_status == params.status.value:
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# ℹ️ Nessuna Modifica Necessaria\n\nL'ad set **{adset_name}** è già nello stato **{params.status.value}**."
            elif params.response_format == ResponseFormat.TOON:
                result = {
                    "success": True,
                    "adset_id": params.adset_id,
                    "adset_name": adset_name,
                    "status": params.status.value,
                    "changed": False,
                    "message": "Ad set già nello stato richiesto"
                }
                return _format_as_toon(result)
            else:
                result = {
                    "success": True,
                    "adset_id": params.adset_id,
                    "adset_name": adset_name,
                    "status": params.status.value,
                    "changed": False,
                    "message": "Ad set già nello stato richiesto"
                }
                return json.dumps(result, indent=2)

        # Esegui l'aggiornamento
        update_data = await _make_api_request(
            params.adset_id,
            method="POST",
            params={
                "status": params.status.value
            }
        )

        if not update_data.get('success'):
            return f"Errore nel cambio stato per ad set {params.adset_id}"

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Stato Ad Set Modificato\n"]
            lines.append(f"**Ad Set**: {adset_name}")
            lines.append(f"**ID**: {params.adset_id}")
            lines.append(f"**Budget**: €{budget/100:.2f}/giorno\n")

            lines.append("## Cambio Stato\n")
            lines.append(f"- **Stato Precedente**: {old_status}")
            lines.append(f"- **Nuovo Stato**: {params.status.value}")

            if params.status == AdSetStatus.ACTIVE:
                lines.append("\n✅ **L'ad set è ora ATTIVO** e sta competendo nelle auction.")
                lines.append("Gli annunci inizieranno a essere mostrati in base al targeting configurato.")
            else:
                lines.append("\n⏸️ **L'ad set è ora IN PAUSA** e non sta spendendo budget.")
                lines.append("Gli annunci non verranno mostrati finché non riattiverai l'ad set.")

            return "\n".join(lines)

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "success": True,
                "adset_id": params.adset_id,
                "adset_name": adset_name,
                "old_status": old_status,
                "new_status": params.status.value,
                "changed": True
            }
            return _format_as_toon(result)
        else:
            result = {
                "success": True,
                "adset_id": params.adset_id,
                "adset_name": adset_name,
                "old_status": old_status,
                "new_status": params.status.value,
                "changed": True
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_update_ad_status",
    annotations={
        "title": "Cambia Stato Annuncio",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def meta_ads_update_ad_status(params: UpdateAdStatusInput) -> str:
    """
    Attiva o mette in pausa un singolo annuncio.

    Questo tool permette di cambiare lo stato di un annuncio tra
    ACTIVE (attivo, può essere mostrato) e PAUSED (in pausa, non viene mostrato).

    Args:
        params (UpdateAdStatusInput): Parametri validati contenenti:
            - ad_id (str): ID dell'annuncio da modificare
            - status (AdStatus): Nuovo stato (ACTIVE o PAUSED)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Conferma del cambio di stato

    Esempi d'uso:
        - "Attiva annuncio 123456789" (status=ACTIVE)
        - "Metti in pausa annuncio 987654321" (status=PAUSED)
        - "Pausa l'ad con performance peggiore"

    Note:
        - Il cambio stato ha effetto immediato
        - Annunci PAUSED non consumano budget e non vengono mostrati
        - Annunci ACTIVE vengono mostrati se l'ad set e la campagna sono attivi
        - L'ad set e la campagna devono essere ACTIVE perché l'annuncio sia erogato
    """
    try:
        # Prima recupera i dati attuali dell'annuncio
        current_data = await _make_api_request(
            params.ad_id,
            params={"fields": "name,status,creative{name}"}
        )

        ad_name = current_data.get('name', params.ad_id)
        old_status = current_data.get('status', 'UNKNOWN')
        creative_name = current_data.get('creative', {}).get('name', 'N/A')

        # Se lo stato è già quello richiesto, comunica che non serve modificare
        if old_status == params.status.value:
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# ℹ️ Nessuna Modifica Necessaria\n\nL'annuncio **{ad_name}** è già nello stato **{params.status.value}**."
            elif params.response_format == ResponseFormat.TOON:
                result = {
                    "success": True,
                    "ad_id": params.ad_id,
                    "ad_name": ad_name,
                    "status": params.status.value,
                    "changed": False,
                    "message": "Annuncio già nello stato richiesto"
                }
                return _format_as_toon(result)
            else:
                result = {
                    "success": True,
                    "ad_id": params.ad_id,
                    "ad_name": ad_name,
                    "status": params.status.value,
                    "changed": False,
                    "message": "Annuncio già nello stato richiesto"
                }
                return json.dumps(result, indent=2)

        # Esegui l'aggiornamento
        update_data = await _make_api_request(
            params.ad_id,
            method="POST",
            params={
                "status": params.status.value
            }
        )

        if not update_data.get('success'):
            return f"Errore nel cambio stato per annuncio {params.ad_id}"

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Stato Annuncio Modificato\n"]
            lines.append(f"**Annuncio**: {ad_name}")
            lines.append(f"**ID**: {params.ad_id}")
            lines.append(f"**Creative**: {creative_name}\n")

            lines.append("## Cambio Stato\n")
            lines.append(f"- **Stato Precedente**: {old_status}")
            lines.append(f"- **Nuovo Stato**: {params.status.value}")

            if params.status == AdStatus.ACTIVE:
                lines.append("\n✅ **L'annuncio è ora ATTIVO** e può essere mostrato.")
                lines.append("Nota: l'annuncio verrà effettivamente erogato solo se anche l'ad set e la campagna sono attivi.")
            else:
                lines.append("\n⏸️ **L'annuncio è ora IN PAUSA** e non verrà mostrato.")
                lines.append("Gli altri annunci nell'ad set continueranno a essere erogati normalmente.")

            return "\n".join(lines)

        elif params.response_format == ResponseFormat.TOON:
            result = {
                "success": True,
                "ad_id": params.ad_id,
                "ad_name": ad_name,
                "old_status": old_status,
                "new_status": params.status.value,
                "changed": True
            }
            return _format_as_toon(result)
        else:
            result = {
                "success": True,
                "ad_id": params.ad_id,
                "ad_name": ad_name,
                "old_status": old_status,
                "new_status": params.status.value,
                "changed": True
            }
            return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_create_campaign",
    annotations={
        "title": "Crea Nuova Campagna",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def meta_ads_create_campaign(params: CreateCampaignInput) -> str:
    """
    Crea una nuova campagna pubblicitaria su Meta Ads.

    Questo tool permette di creare una campagna con nome, obiettivo, budget e stato.
    La campagna viene creata in stato PAUSED di default per permettere la configurazione
    degli ad set e annunci prima di attivarla.

    Args:
        params (CreateCampaignInput): Parametri validati contenenti:
            - account_id (str): ID account (formato 'act_123456789')
            - name (str): Nome della campagna (1-400 caratteri)
            - objective (CampaignObjective): Obiettivo (OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT,
              OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_TRAFFIC, OUTCOME_APP_PROMOTION)
            - status (CampaignStatus): Stato iniziale (default: PAUSED)
            - daily_budget (Optional[int]): Budget giornaliero in centesimi (min €1 = 100)
            - lifetime_budget (Optional[int]): Budget totale in centesimi (alternativa a daily_budget)
            - special_ad_categories (Optional[List[str]]): Per categorie speciali (credito, lavoro, casa, politica)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: ID della campagna creata con conferma e dettagli

    Esempi d'uso:
        - "Crea campagna 'Promo Estate 2025' per vendite con budget €50/giorno"
        - "Nuova campagna awareness 'Brand Launch' con budget lifetime €500"
        - "Crea campagna lead generation con budget €30/giorno"

    Note:
        - Devi specificare SOLO uno tra daily_budget o lifetime_budget
        - La campagna viene creata in PAUSED per sicurezza
        - Dopo la creazione, dovrai creare almeno un ad set e un annuncio
        - Per categorie speciali (credito, lavoro, casa, politica) devi specificare special_ad_categories
    """
    try:
        # Prepara i parametri della campagna
        campaign_params = {
            "name": params.name,
            "objective": params.objective.value,
            "status": params.status.value
        }

        # Aggiungi budget (solo uno dei due)
        if params.daily_budget is not None:
            campaign_params["daily_budget"] = params.daily_budget
        elif params.lifetime_budget is not None:
            campaign_params["lifetime_budget"] = params.lifetime_budget

        # Aggiungi categorie speciali se presenti
        if params.special_ad_categories:
            campaign_params["special_ad_categories"] = json.dumps(params.special_ad_categories)

        # Crea la campagna
        endpoint = f"{params.account_id}/campaigns"
        result = await _make_api_request(
            endpoint,
            method="POST",
            params=campaign_params
        )

        campaign_id = result.get('id')
        if not campaign_id:
            return "Errore: Campagna non creata. Verifica i parametri."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Campagna Creata con Successo\n"]
            lines.append(f"**Nome**: {params.name}")
            lines.append(f"**ID**: {campaign_id}")
            lines.append(f"**Account**: {params.account_id}\n")

            lines.append("## Configurazione\n")
            lines.append(f"- **Obiettivo**: {params.objective.value}")
            lines.append(f"- **Stato**: {params.status.value}")

            if params.daily_budget:
                lines.append(f"- **Budget Giornaliero**: €{params.daily_budget/100:.2f}")
            elif params.lifetime_budget:
                lines.append(f"- **Budget Lifetime**: €{params.lifetime_budget/100:.2f}")

            if params.special_ad_categories:
                lines.append(f"- **Categorie Speciali**: {', '.join(params.special_ad_categories)}")

            lines.append("\n## Prossimi Passi\n")
            lines.append("1. ✅ Campagna creata")
            lines.append(f"2. ⏭️ Crea ad set con `meta_ads_create_adset` usando campaign_id: {campaign_id}")
            lines.append("3. ⏭️ Crea annunci nell'ad set")
            lines.append(f"4. ⏭️ Attiva la campagna con `meta_ads_update_campaign_status` quando pronto")

            if params.status == CampaignStatus.PAUSED:
                lines.append("\n⏸️ *La campagna è in stato PAUSED. Configurala completamente prima di attivarla.*")

            return "\n".join(lines)

        else:
            result_data = {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_name": params.name,
                "account_id": params.account_id,
                "objective": params.objective.value,
                "status": params.status.value
            }
            if params.daily_budget:
                result_data["daily_budget"] = params.daily_budget
            if params.lifetime_budget:
                result_data["lifetime_budget"] = params.lifetime_budget
            return json.dumps(result_data, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_create_adset",
    annotations={
        "title": "Crea Nuovo Ad Set",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def meta_ads_create_adset(params: CreateAdSetInput) -> str:
    """
    Crea un nuovo ad set all'interno di una campagna esistente.

    Questo tool permette di creare un ad set con targeting, budget, ottimizzazione
    e scheduling. L'ad set viene creato in stato PAUSED di default per permettere
    la configurazione degli annunci prima di attivarlo.

    Args:
        params (CreateAdSetInput): Parametri validati contenenti:
            - campaign_id (str): ID campagna a cui associare l'ad set
            - name (str): Nome dell'ad set (1-400 caratteri)
            - optimization_goal (OptimizationGoal): Obiettivo ottimizzazione (REACH, IMPRESSIONS,
              LINK_CLICKS, LANDING_PAGE_VIEWS, OFFSITE_CONVERSIONS, QUALITY_LEAD, VALUE, THRUPLAY)
            - billing_event (BillingEvent): Evento fatturazione (IMPRESSIONS, LINK_CLICKS, THRUPLAY)
            - targeting (Dict): Oggetto targeting. OBBLIGATORI: geo_locations e targeting_automation.advantage_audience. Esempio:
              {'geo_locations': {'countries': ['IT']}, 'age_min': 25, 'age_max': 55, 'targeting_automation': {'advantage_audience': 0}}
            - bid_amount (Optional[int]): Importo bid in centesimi. OBBLIGATORIO per LINK_CLICKS, LANDING_PAGE_VIEWS e altri goals
            - daily_budget (Optional[int]): Budget giornaliero in centesimi (se campagna senza budget)
            - lifetime_budget (Optional[int]): Budget lifetime in centesimi (alternativa a daily_budget)
            - start_time (Optional[str]): Data/ora inizio (ISO 8601, es: '2025-01-15T00:00:00+0100')
            - end_time (Optional[str]): Data/ora fine (ISO 8601, opzionale)
            - status (AdSetStatus): Stato iniziale (default: PAUSED)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: ID dell'ad set creato con conferma e dettagli

    Esempi d'uso:
        - "Crea ad set 'Italia 25-55' per campagna 123456 targeting Italia con budget €20/giorno"
        - "Nuovo ad set ottimizzato per conversioni con targeting uomini 30-50 Roma"
        - "Crea ad set per link clicks budget €15/giorno targeting donne 25-45"

    Note:
        - Il targeting deve includere OBBLIGATORIAMENTE:
          * geo_locations (paesi, regioni o città)
          * targeting_automation.advantage_audience (0=disabilitato, 1=abilitato)
        - bid_amount è OBBLIGATORIO per optimization goals come LINK_CLICKS, LANDING_PAGE_VIEWS, ecc.
        - Budget: NON specificare daily_budget/lifetime_budget se la campagna ha già un budget
        - Non specificare sia daily_budget che lifetime_budget contemporaneamente
        - L'ad set viene creato in PAUSED per sicurezza
        - Dopo la creazione, dovrai creare almeno un annuncio nell'ad set
    """
    try:
        # Prepara i parametri dell'ad set
        adset_params = {
            "name": params.name,
            "campaign_id": params.campaign_id,
            "optimization_goal": params.optimization_goal.value,
            "billing_event": params.billing_event.value,
            "targeting": json.dumps(params.targeting),
            "status": params.status.value
        }

        # Aggiungi bid amount se specificato
        if params.bid_amount is not None:
            adset_params["bid_amount"] = params.bid_amount

        # Aggiungi budget se specificato (opzionale se già impostato a livello campagna)
        if params.daily_budget is not None:
            adset_params["daily_budget"] = params.daily_budget
        elif params.lifetime_budget is not None:
            adset_params["lifetime_budget"] = params.lifetime_budget

        # Aggiungi scheduling se specificato
        if params.start_time:
            adset_params["start_time"] = params.start_time
        if params.end_time:
            adset_params["end_time"] = params.end_time

        # Recupera l'account_id dalla campagna
        campaign_fields = await _make_api_request(
            params.campaign_id,
            params={"fields": "account_id"}
        )
        account_id = campaign_fields.get('account_id', '')
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'

        # Crea l'ad set usando l'account_id
        endpoint = f"{account_id}/adsets"
        result = await _make_api_request(
            endpoint,
            method="POST",
            params=adset_params
        )

        adset_id = result.get('id')
        if not adset_id:
            return "Errore: Ad set non creato. Verifica i parametri."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Ad Set Creato con Successo\n"]
            lines.append(f"**Nome**: {params.name}")
            lines.append(f"**ID**: {adset_id}")
            lines.append(f"**Campagna**: {params.campaign_id}\n")

            lines.append("## Configurazione\n")
            lines.append(f"- **Obiettivo Ottimizzazione**: {params.optimization_goal.value}")
            lines.append(f"- **Evento Fatturazione**: {params.billing_event.value}")
            lines.append(f"- **Stato**: {params.status.value}")

            if params.bid_amount:
                lines.append(f"- **Bid Amount**: €{params.bid_amount/100:.2f}")

            if params.daily_budget:
                lines.append(f"- **Budget Giornaliero**: €{params.daily_budget/100:.2f}")
            elif params.lifetime_budget:
                lines.append(f"- **Budget Lifetime**: €{params.lifetime_budget/100:.2f}")

            lines.append("\n## Targeting\n")
            targeting = params.targeting

            # Geo targeting
            geo = targeting.get('geo_locations', {})
            if 'countries' in geo:
                lines.append(f"- **Paesi**: {', '.join(geo['countries'])}")
            if 'regions' in geo:
                lines.append(f"- **Regioni**: {len(geo['regions'])} regioni")
            if 'cities' in geo:
                lines.append(f"- **Città**: {len(geo['cities'])} città")

            # Demographic targeting
            if 'age_min' in targeting or 'age_max' in targeting:
                age_min = targeting.get('age_min', 18)
                age_max = targeting.get('age_max', 65)
                lines.append(f"- **Età**: {age_min}-{age_max} anni")

            if 'genders' in targeting:
                gender_map = {1: 'Uomini', 2: 'Donne'}
                genders_str = ', '.join([gender_map.get(g, str(g)) for g in targeting['genders']])
                lines.append(f"- **Genere**: {genders_str}")

            # Scheduling
            if params.start_time or params.end_time:
                lines.append("\n## Scheduling\n")
                if params.start_time:
                    lines.append(f"- **Inizio**: {params.start_time}")
                if params.end_time:
                    lines.append(f"- **Fine**: {params.end_time}")

            lines.append("\n## Prossimi Passi\n")
            lines.append("1. ✅ Ad set creato")
            lines.append(f"2. ⏭️ Crea annunci nell'ad set {adset_id}")
            lines.append("3. ⏭️ Attiva l'ad set con `meta_ads_update_adset_status` quando pronto")

            if params.status == AdSetStatus.PAUSED:
                lines.append("\n⏸️ *L'ad set è in stato PAUSED. Crea gli annunci prima di attivarlo.*")

            return "\n".join(lines)

        else:
            result_data = {
                "success": True,
                "adset_id": adset_id,
                "adset_name": params.name,
                "campaign_id": params.campaign_id,
                "optimization_goal": params.optimization_goal.value,
                "billing_event": params.billing_event.value,
                "status": params.status.value,
                "targeting": params.targeting
            }
            if params.bid_amount:
                result_data["bid_amount"] = params.bid_amount
            if params.daily_budget:
                result_data["daily_budget"] = params.daily_budget
            if params.lifetime_budget:
                result_data["lifetime_budget"] = params.lifetime_budget
            return json.dumps(result_data, indent=2)

    except Exception as e:
        return _handle_api_error(e)


# =============================================================================
# MULTI-LANGUAGE ADS - Modelli e Tool per annunci multilingua
# =============================================================================

class SearchLocalesInput(BaseModel):
    """Input per cercare locale IDs per Multi-Language Ads."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    query: str = Field(
        ...,
        description="Nome della lingua da cercare (es. 'italian', 'french', 'german')",
        min_length=1
    )
    limit: Optional[int] = Field(
        default=20,
        description="Numero massimo di risultati (1-100)",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )


class LanguageAsset(BaseModel):
    """Definisce i testi per una singola lingua in un Multi-Language Ad."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    label: str = Field(
        ...,
        description="Etichetta identificativa della lingua in formato ISO (es. 'en_XX', 'it_IT', 'de_DE', 'fr_XX', 'pl_PL'). Codici comuni: en_XX (inglese), it_IT (italiano), de_DE (tedesco), fr_XX (francese), es_XX (spagnolo), pl_PL (polacco), pt_PT (portoghese)",
        min_length=2,
        max_length=10
    )
    locale_ids: List[int] = Field(
        ...,
        description="Lista di locale IDs per questa lingua (es. [6, 24] per inglese US+UK, [28] per italiano). Usa meta_ads_search_locales per trovarli",
        min_length=1
    )
    body: str = Field(
        ...,
        description="Testo principale dell'annuncio (max 4096 caratteri)",
        min_length=1,
        max_length=4096
    )
    title: str = Field(
        ...,
        description="Titolo dell'annuncio (max 255 caratteri)",
        min_length=1,
        max_length=255
    )
    description: str = Field(
        default="",
        description="Descrizione secondaria (max 10000 caratteri). Può essere vuoto ''",
        max_length=10000
    )
    link_url: str = Field(
        ...,
        description="URL di destinazione per questa lingua",
        min_length=1
    )
    display_url: Optional[str] = Field(
        default=None,
        description="URL visualizzato nell'annuncio (opzionale, es. 'example.com'). Se non specificato, viene estratto da link_url"
    )
    is_default: bool = Field(
        default=False,
        description="Se True, questa lingua sarà quella di default per utenti con locale non corrispondente"
    )


class CallToActionType(str, Enum):
    """Tipi di Call to Action disponibili."""
    SHOP_NOW = "SHOP_NOW"
    LEARN_MORE = "LEARN_MORE"
    SIGN_UP = "SIGN_UP"
    SUBSCRIBE = "SUBSCRIBE"
    CONTACT_US = "CONTACT_US"
    GET_QUOTE = "GET_QUOTE"
    APPLY_NOW = "APPLY_NOW"
    BOOK_NOW = "BOOK_NOW"
    DOWNLOAD = "DOWNLOAD"
    GET_OFFER = "GET_OFFER"
    GET_DIRECTIONS = "GET_DIRECTIONS"
    SEND_MESSAGE = "SEND_MESSAGE"
    WATCH_MORE = "WATCH_MORE"
    ORDER_NOW = "ORDER_NOW"
    BUY_NOW = "BUY_NOW"


class AdFormat(str, Enum):
    """Formati annuncio supportati per Multi-Language Ads."""
    SINGLE_IMAGE = "SINGLE_IMAGE"
    SINGLE_VIDEO = "SINGLE_VIDEO"


class CreateMultiLangAdInput(BaseModel):
    """Input per creare un annuncio Multi-Language."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    account_id: str = Field(
        ...,
        description="ID dell'account pubblicitario (formato: 'act_123456789' o solo '123456789')",
        min_length=1
    )
    adset_id: str = Field(
        ...,
        description="ID dell'ad set in cui creare l'annuncio",
        min_length=1
    )
    name: str = Field(
        ...,
        description="Nome dell'annuncio",
        min_length=1,
        max_length=400
    )
    page_id: str = Field(
        ...,
        description="ID della pagina Facebook associata",
        min_length=1
    )
    instagram_user_id: Optional[str] = Field(
        default=None,
        description="ID dell'account Instagram (opzionale, per placement Instagram). Deve essere l'instagram_user_id, non instagram_actor_id"
    )
    ad_format: AdFormat = Field(
        default=AdFormat.SINGLE_IMAGE,
        description="Formato annuncio: SINGLE_IMAGE o SINGLE_VIDEO"
    )
    image_hash: Optional[str] = Field(
        default=None,
        description="Hash dell'immagine (richiesto per SINGLE_IMAGE). Ottienilo dalla libreria immagini dell'account"
    )
    video_id: Optional[str] = Field(
        default=None,
        description="ID del video (richiesto per SINGLE_VIDEO). Ottienilo dalla libreria video dell'account"
    )
    languages: List[LanguageAsset] = Field(
        ...,
        description="Lista delle lingue con i relativi testi. Deve contenere esattamente una lingua con is_default=True",
        min_length=1
    )
    call_to_action: CallToActionType = Field(
        default=CallToActionType.LEARN_MORE,
        description="Tipo di Call to Action"
    )
    status: AdStatus = Field(
        default=AdStatus.PAUSED,
        description="Stato iniziale dell'annuncio (default: PAUSED)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Assicura che l'account ID abbia il prefisso corretto."""
        if not v.startswith('act_'):
            return f'act_{v}'
        return v

    @field_validator('languages')
    @classmethod
    def validate_languages(cls, v: List[LanguageAsset]) -> List[LanguageAsset]:
        """Valida che ci sia esattamente una lingua default."""
        defaults = [lang for lang in v if lang.is_default]
        if len(defaults) == 0:
            raise ValueError("Devi specificare esattamente una lingua con is_default=True")
        if len(defaults) > 1:
            raise ValueError("Solo una lingua può avere is_default=True")
        return v

    @field_validator('image_hash')
    @classmethod
    def validate_media(cls, v: Optional[str], info) -> Optional[str]:
        """Valida che sia presente il media corretto per il formato scelto."""
        ad_format = info.data.get('ad_format')
        video_id = info.data.get('video_id')

        if ad_format == AdFormat.SINGLE_IMAGE and not v:
            raise ValueError("image_hash è richiesto per il formato SINGLE_IMAGE")
        if ad_format == AdFormat.SINGLE_VIDEO and not video_id:
            raise ValueError("video_id è richiesto per il formato SINGLE_VIDEO")
        return v


class UpdateAdLanguagesInput(BaseModel):
    """Input per aggiornare le lingue di un annuncio esistente."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    ad_id: str = Field(
        ...,
        description="ID dell'annuncio da modificare",
        min_length=1
    )
    languages: List[LanguageAsset] = Field(
        ...,
        description="Nuova lista completa delle lingue. Sostituirà completamente quella esistente",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Formato output"
    )

    @field_validator('languages')
    @classmethod
    def validate_languages(cls, v: List[LanguageAsset]) -> List[LanguageAsset]:
        """Valida che ci sia esattamente una lingua default."""
        defaults = [lang for lang in v if lang.is_default]
        if len(defaults) == 0:
            raise ValueError("Devi specificare esattamente una lingua con is_default=True")
        if len(defaults) > 1:
            raise ValueError("Solo una lingua può avere is_default=True")
        return v


@mcp.tool(
    name="meta_ads_search_locales",
    annotations={
        "title": "Cerca Locale IDs per Multi-Language Ads",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def meta_ads_search_locales(params: SearchLocalesInput) -> str:
    """
    Cerca i locale IDs supportati per gli annunci Multi-Language.

    I locale IDs sono necessari per configurare le regole di personalizzazione
    degli annunci multilingua. Ogni lingua ha uno o più locale IDs associati.

    Args:
        params (SearchLocalesInput): Parametri validati contenenti:
            - query (str): Nome della lingua da cercare (es. 'italian', 'french')
            - limit (int): Numero massimo di risultati (default: 20)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Lista dei locale trovati con ID e nome.

    Esempi d'uso:
        - "Cerca locale per italiano" → Ritorna locale ID 28 (Italian)
        - "Cerca locale per english" → Ritorna locale IDs 6 (English US), 24 (English UK)
        - "Cerca locale per french" → Ritorna locale IDs per francese

    Note:
        - Usa i locale IDs ritornati nel campo 'locale_ids' di LanguageAsset
        - Puoi assegnare più locale IDs alla stessa lingua (es. [6, 24] per tutti gli inglesi)
        - Locale comuni: 6=English US, 24=English UK, 28=Italian, 9=French, 5=German
    """
    try:
        # Chiama l'endpoint di ricerca locales
        result = await _make_api_request(
            "search",
            method="GET",
            params={
                "type": "adlocale",
                "q": params.query,
                "limit": params.limit
            }
        )

        locales = result.get('data', [])

        if params.response_format == ResponseFormat.MARKDOWN:
            if not locales:
                return f"# Nessun locale trovato per '{params.query}'\n\nProva con un altro termine di ricerca in inglese (es. 'italian', 'french', 'german')."

            lines = [f"# Locale IDs per '{params.query}'\n"]
            lines.append(f"Trovati **{len(locales)}** locale(s):\n")
            lines.append("| ID | Nome |")
            lines.append("|---:|:-----|")

            for locale in locales:
                lines.append(f"| {locale.get('key')} | {locale.get('name')} |")

            lines.append("\n## Come usare")
            lines.append("Usa questi IDs nel campo `locale_ids` quando crei un annuncio multilingua:")
            lines.append("```json")
            lines.append("{")
            lines.append(f'  "label": "{params.query}",')
            lines.append(f'  "locale_ids": [{locales[0].get("key")}],')
            lines.append('  "body": "Testo annuncio...",')
            lines.append('  ...')
            lines.append("}")
            lines.append("```")

            return "\n".join(lines)

        else:
            return json.dumps({
                "query": params.query,
                "count": len(locales),
                "locales": [{"id": l.get('key'), "name": l.get('name')} for l in locales]
            }, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_create_multilang_ad",
    annotations={
        "title": "Crea Annuncio Multi-Lingua",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def meta_ads_create_multilang_ad(params: Any) -> str:
    """
    Crea un annuncio pubblicitario con supporto per più lingue.

    Gli annunci multilingua permettono di mostrare automaticamente la versione
    nella lingua corretta in base alle preferenze dell'utente. Facebook ottimizza
    la delivery per mostrare la lingua più appropriata a ciascun utente.

    Args:
        params (CreateMultiLangAdInput): Parametri validati contenenti:
            - account_id (str): ID account (formato 'act_123456789')
            - adset_id (str): ID dell'ad set di destinazione
            - name (str): Nome dell'annuncio
            - page_id (str): ID della pagina Facebook
            - instagram_user_id (Optional[str]): ID account Instagram (dentro object_story_spec)
            - ad_format (AdFormat): SINGLE_IMAGE o SINGLE_VIDEO
            - image_hash (str): Hash immagine (per SINGLE_IMAGE)
            - video_id (str): ID video (per SINGLE_VIDEO)
            - languages (List[LanguageAsset]): Lista lingue con testi
            - call_to_action (CallToActionType): Tipo CTA
            - status (AdStatus): Stato iniziale (default: PAUSED)
            - response_format (ResponseFormat): Formato output

    Returns:
        str: ID dell'annuncio creato con conferma e dettagli

    Esempi d'uso:
        - "Crea annuncio multilingua italiano/inglese per promozione estate"
        - "Nuovo ad con testi in IT, EN, FR per campagna europea"

    Note:
        - Usa prima meta_ads_search_locales per trovare i locale IDs
        - Esattamente una lingua deve avere is_default=True
        - La lingua default viene mostrata agli utenti con locale non corrispondente
        - Supporta solo SINGLE_IMAGE e SINGLE_VIDEO (no carousel)
    """
    try:
        # Gestisci il caso in cui params arrivi come stringa JSON
        if isinstance(params, str):
            params = CreateMultiLangAdInput(**json.loads(params))
        elif isinstance(params, dict):
            params = CreateMultiLangAdInput(**params)
        elif not isinstance(params, CreateMultiLangAdInput):
            return f"Errore: tipo di parametro non valido: {type(params)}"
        # Trova la lingua default per usare la sua label per l'immagine condivisa
        default_lang = next((lang for lang in params.languages if lang.is_default), params.languages[0])
        default_label = default_lang.label

        # Costruisci l'asset_feed_spec
        bodies = []
        titles = []
        descriptions = []
        link_urls = []
        asset_customization_rules = []

        for lang in params.languages:
            # Aggiungi gli asset con label
            bodies.append({
                "text": lang.body,
                "adlabels": [{"name": lang.label}]
            })
            titles.append({
                "text": lang.title,
                "adlabels": [{"name": lang.label}]
            })
            descriptions.append({
                "text": lang.description,
                "adlabels": [{"name": lang.label}]
            })

            # Link URL con display_url
            link_url_entry = {
                "website_url": lang.link_url,
                "adlabels": [{"name": lang.label}]
            }
            # Aggiungi display_url se specificato, altrimenti estrai dal dominio
            if lang.display_url:
                link_url_entry["display_url"] = lang.display_url
            else:
                # Estrai dominio dall'URL come display_url
                parsed = urlparse(lang.link_url)
                link_url_entry["display_url"] = parsed.netloc or lang.link_url
            link_urls.append(link_url_entry)

            # Crea la regola di customizzazione per questa lingua
            rule = {
                "customization_spec": {
                    "locales": lang.locale_ids
                },
                # image_label punta sempre all'immagine condivisa (label della lingua default)
                "image_label": {"name": default_label},
                "body_label": {"name": lang.label},
                "title_label": {"name": lang.label},
                "description_label": {"name": lang.label},
                "link_url_label": {"name": lang.label}
            }

            if lang.is_default:
                rule["is_default"] = True

            asset_customization_rules.append(rule)

        # Prepara l'asset_feed_spec con optimization_type: LANGUAGE
        asset_feed_spec = {
            "optimization_type": "LANGUAGE",
            "ad_formats": [params.ad_format.value],
            "bodies": bodies,
            "titles": titles,
            "descriptions": descriptions,
            "link_urls": link_urls,
            "call_to_action_types": [params.call_to_action.value],
            "asset_customization_rules": asset_customization_rules
        }

        # Aggiungi immagine o video con adlabels della lingua default
        if params.ad_format == AdFormat.SINGLE_IMAGE:
            asset_feed_spec["images"] = [{
                "hash": params.image_hash,
                "adlabels": [{"name": default_label}]
            }]
        else:
            asset_feed_spec["videos"] = [{
                "video_id": params.video_id,
                "adlabels": [{"name": default_label}]
            }]

        # Prepara object_story_spec
        object_story_spec = {
            "page_id": params.page_id
        }
        if params.instagram_user_id:
            object_story_spec["instagram_user_id"] = params.instagram_user_id

        # Crea il creative
        creative_result = await _make_api_request(
            f"{params.account_id}/adcreatives",
            method="POST",
            params={
                "object_story_spec": json.dumps(object_story_spec),
                "asset_feed_spec": json.dumps(asset_feed_spec)
            }
        )

        creative_id = creative_result.get('id')
        if not creative_id:
            return "Errore: Creative non creato. Verifica i parametri."

        # Crea l'annuncio con il creative
        ad_result = await _make_api_request(
            f"{params.account_id}/ads",
            method="POST",
            params={
                "name": params.name,
                "adset_id": params.adset_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": params.status.value
            }
        )

        ad_id = ad_result.get('id')
        if not ad_id:
            return f"Errore: Annuncio non creato (creative_id: {creative_id}). Verifica i parametri."

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Annuncio Multi-Lingua Creato\n"]
            lines.append(f"**Nome**: {params.name}")
            lines.append(f"**ID Annuncio**: {ad_id}")
            lines.append(f"**ID Creative**: {creative_id}")
            lines.append(f"**Ad Set**: {params.adset_id}")
            lines.append(f"**Stato**: {params.status.value}\n")

            lines.append("## Lingue Configurate\n")
            for lang in params.languages:
                default_marker = " ⭐ (default)" if lang.is_default else ""
                lines.append(f"### {lang.label.capitalize()}{default_marker}")
                lines.append(f"- **Locale IDs**: {lang.locale_ids}")
                lines.append(f"- **Titolo**: {lang.title[:50]}{'...' if len(lang.title) > 50 else ''}")
                lines.append(f"- **Body**: {lang.body[:80]}{'...' if len(lang.body) > 80 else ''}")
                lines.append(f"- **Link**: {lang.link_url}\n")

            lines.append("## Configurazione\n")
            lines.append(f"- **Formato**: {params.ad_format.value}")
            lines.append(f"- **CTA**: {params.call_to_action.value}")
            lines.append(f"- **Pagina**: {params.page_id}")
            if params.instagram_user_id:
                lines.append(f"- **Instagram**: {params.instagram_user_id}")

            if params.status == AdStatus.PAUSED:
                lines.append("\n⏸️ *L'annuncio è in stato PAUSED. Attivalo con `meta_ads_update_ad_status` quando pronto.*")

            return "\n".join(lines)

        else:
            return json.dumps({
                "success": True,
                "ad_id": ad_id,
                "creative_id": creative_id,
                "ad_name": params.name,
                "adset_id": params.adset_id,
                "status": params.status.value,
                "languages": [
                    {
                        "label": lang.label,
                        "locale_ids": lang.locale_ids,
                        "is_default": lang.is_default
                    }
                    for lang in params.languages
                ]
            }, indent=2)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="meta_ads_update_ad_languages",
    annotations={
        "title": "Aggiorna Lingue Annuncio",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def meta_ads_update_ad_languages(params: Any) -> str:
    """
    Aggiorna le lingue di un annuncio esistente.

    Questo tool permette di modificare i testi multilingua di un annuncio
    aggiornando l'asset_feed_spec del creative associato.

    ATTENZIONE: Questa operazione sostituisce COMPLETAMENTE le lingue esistenti.
    Devi fornire tutte le lingue desiderate, non solo quelle da modificare.

    Args:
        params (UpdateAdLanguagesInput): Parametri validati contenenti:
            - ad_id (str): ID dell'annuncio da modificare
            - languages (List[LanguageAsset]): Nuova lista completa delle lingue
            - response_format (ResponseFormat): Formato output

    Returns:
        str: Conferma dell'aggiornamento con dettagli

    Esempi d'uso:
        - "Aggiorna testi italiano dell'annuncio 123456"
        - "Aggiungi tedesco all'annuncio multilingua esistente"
        - "Modifica tutti i testi dell'annuncio"

    Note:
        - Le lingue fornite SOSTITUISCONO completamente quelle esistenti
        - Per aggiungere una lingua, includi tutte le lingue esistenti + la nuova
        - Esattamente una lingua deve avere is_default=True
        - L'aggiornamento è immediato
    """
    try:
        # Gestisci il caso in cui params arrivi come stringa JSON
        if isinstance(params, str):
            params = UpdateAdLanguagesInput(**json.loads(params))
        elif isinstance(params, dict):
            params = UpdateAdLanguagesInput(**params)
        elif not isinstance(params, UpdateAdLanguagesInput):
            return f"Errore: tipo di parametro non valido: {type(params)}"

        # Prima recupera i dati dell'annuncio per ottenere il creative_id
        ad_data = await _make_api_request(
            params.ad_id,
            method="GET",
            params={
                "fields": "creative{id,object_story_spec,asset_feed_spec}"
            }
        )

        creative_data = ad_data.get('creative', {})
        creative_id = creative_data.get('id')

        if not creative_id:
            return "Errore: Impossibile recuperare il creative dell'annuncio. Verifica l'ID."

        # Recupera l'asset_feed_spec esistente per mantenere le immagini/video
        existing_asset_feed = creative_data.get('asset_feed_spec', {})
        existing_object_story = creative_data.get('object_story_spec', {})

        # Trova la lingua default per usare la sua label per l'immagine condivisa
        default_lang = next((lang for lang in params.languages if lang.is_default), params.languages[0])
        default_label = default_lang.label

        # Costruisci il nuovo asset_feed_spec con le nuove lingue
        bodies = []
        titles = []
        descriptions = []
        link_urls = []
        call_to_actions = []
        asset_customization_rules = []

        # Recupera il tipo di CTA esistente
        existing_cta = 'LEARN_MORE'
        if existing_asset_feed.get('call_to_actions'):
            existing_cta = existing_asset_feed['call_to_actions'][0].get('type', 'LEARN_MORE')
        elif existing_asset_feed.get('call_to_action_types'):
            existing_cta = existing_asset_feed['call_to_action_types'][0]

        for lang in params.languages:
            bodies.append({
                "text": lang.body,
                "adlabels": [{"name": lang.label}]
            })
            titles.append({
                "text": lang.title,
                "adlabels": [{"name": lang.label}]
            })
            descriptions.append({
                "text": lang.description,
                "adlabels": [{"name": lang.label}]
            })

            # Link URL con display_url
            link_url_entry = {
                "website_url": lang.link_url,
                "adlabels": [{"name": lang.label}]
            }
            # Aggiungi display_url se specificato, altrimenti estrai dal dominio
            if lang.display_url:
                link_url_entry["display_url"] = lang.display_url
            else:
                parsed = urlparse(lang.link_url)
                link_url_entry["display_url"] = parsed.netloc or lang.link_url
            link_urls.append(link_url_entry)

            # Call to action per lingua
            call_to_actions.append({
                "type": existing_cta,
                "adlabels": [{"name": lang.label}]
            })

            rule = {
                "customization_spec": {
                    "locales": lang.locale_ids
                },
                # image_label punta sempre all'immagine condivisa (label della lingua default)
                "image_label": {"name": default_label},
                "body_label": {"name": lang.label},
                "title_label": {"name": lang.label},
                "description_label": {"name": lang.label},
                "link_url_label": {"name": lang.label},
                "call_to_action_type_label": {"name": lang.label}
            }

            if lang.is_default:
                rule["is_default"] = True

            asset_customization_rules.append(rule)

        # Costruisci il nuovo asset_feed_spec con optimization_type: LANGUAGE
        new_asset_feed_spec = {
            "optimization_type": "LANGUAGE",
            "ad_formats": existing_asset_feed.get('ad_formats', ['SINGLE_IMAGE']),
            "bodies": bodies,
            "titles": titles,
            "descriptions": descriptions,
            "link_urls": link_urls,
            "call_to_actions": call_to_actions,
            "asset_customization_rules": asset_customization_rules
        }

        # Mantieni immagini o video esistenti, aggiornando adlabels con la label default
        if 'images' in existing_asset_feed:
            updated_images = []
            for img in existing_asset_feed['images']:
                updated_img = {**img, "adlabels": [{"name": default_label}]}
                updated_images.append(updated_img)
            new_asset_feed_spec['images'] = updated_images
        if 'videos' in existing_asset_feed:
            updated_videos = []
            for vid in existing_asset_feed['videos']:
                updated_vid = {**vid, "adlabels": [{"name": default_label}]}
                updated_videos.append(updated_vid)
            new_asset_feed_spec['videos'] = updated_videos

        # Aggiorna il creative
        await _make_api_request(
            creative_id,
            method="POST",
            params={
                "asset_feed_spec": json.dumps(new_asset_feed_spec)
            }
        )

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = ["# ✅ Lingue Annuncio Aggiornate\n"]
            lines.append(f"**ID Annuncio**: {params.ad_id}")
            lines.append(f"**ID Creative**: {creative_id}\n")

            lines.append("## Nuove Lingue Configurate\n")
            for lang in params.languages:
                default_marker = " ⭐ (default)" if lang.is_default else ""
                lines.append(f"### {lang.label.capitalize()}{default_marker}")
                lines.append(f"- **Locale IDs**: {lang.locale_ids}")
                lines.append(f"- **Titolo**: {lang.title[:50]}{'...' if len(lang.title) > 50 else ''}")
                lines.append(f"- **Body**: {lang.body[:80]}{'...' if len(lang.body) > 80 else ''}")
                lines.append(f"- **Link**: {lang.link_url}\n")

            lines.append("---")
            lines.append("*Le modifiche sono attive immediatamente.*")

            return "\n".join(lines)

        else:
            return json.dumps({
                "success": True,
                "ad_id": params.ad_id,
                "creative_id": creative_id,
                "languages_updated": len(params.languages),
                "languages": [
                    {
                        "label": lang.label,
                        "locale_ids": lang.locale_ids,
                        "is_default": lang.is_default
                    }
                    for lang in params.languages
                ]
            }, indent=2)

    except Exception as e:
        return _handle_api_error(e)


if __name__ == "__main__":
    # Avvia il server MCP
    mcp.run()
