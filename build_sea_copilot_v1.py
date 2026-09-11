#!/usr/bin/env python3
"""Generate SEA Copilot n8n workflow JSON exports (chat + ingest)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

SYSTEM_MESSAGE = """Tu es le copilote stratégique d'un fondateur d'agence SEA (Search Engine Advertising / Meta Ads).

RÔLE
- Aider à prioriser les actions sur les comptes clients Meta Ads.
- Parler comme un directeur de compte senior : clair, orienté rétention client et marge agence.
- Jamais de jargon technique inutile (pas de « embedding », « token », « API » sauf si le fondateur demande).

OUTILS — QUAND LES UTILISER
1. meta_compte_live : dès qu'on parle de performance actuelle, campagnes, ROAS, budget, alertes. Toujours appeler avant de conclure sur l'état « live » d'un compte.
2. search_rapports_meta (si disponible) : pour retrouver l'historique narratif (rapports passés, décisions, contexte client). Utiliser quand on compare avec le passé ou qu'on cherche « ce qu'on avait dit en avril ».

MÉMOIRE
- La mémoire de session garde le fil de la conversation en cours.
- Le vector store garde les rapports archivés — ce ne sont pas la même chose.

FORMAT D'ANALYSE COMPTE (4 sections obligatoires quand tu analyses un compte)
1. **Ce qui va bien** — 2-3 bullets max, chiffrés si possible.
2. **Ce qui décroche** — campagnes ou signaux à risque, avec impact business client.
3. **Actions 48h** — 2-3 actions concrètes (pas une liste de 10 tâches).
4. **Message client** — brouillon court (3-5 phrases) que le fondateur peut envoyer tel quel ou adapter.

RÈGLES
- Si les données live contredisent une intuition, fais confiance aux données.
- Toujours relier performance ads → satisfaction client → rétention contrat agence.
- En mode démo, le compte type est « Lumière Paris » — assume ce contexte si non précisé.
- Réponds en français."""

META_TOOL_JS = r"""const demo = {
  account: {
    name: 'Lumière Paris — E-commerce Mode',
    id: 'act_284719305612847',
    currency: 'EUR',
    status: 'ACTIVE',
    agency: 'Agence Horizon SEA',
  },
  period: { label: '30 derniers jours — Mai 2026', since: '2026-04-06', until: '2026-05-05' },
  totals: { spend_eur: 12830, roas: 3.42, conversions: 504, cpa_eur: 25.46 },
  campaigns: [
    { name: 'Prospection — Lookalike Acheteurs 180j', spend: 4280, roas: 5.65, signal: 'TOP' },
    { name: 'Conversion — Catalogue Dynamique', spend: 3150, roas: 6.3, signal: 'TOP' },
    {
      name: 'Retargeting — Panier Abandon 7j',
      spend: 2840,
      roas: 1.18,
      roas_prev: 2.45,
      signal: 'DÉCROCHE',
      note: 'Budget +30%, ROAS divisé par ~2 — priorité rétention',
    },
    { name: 'Notoriété — Vidéo UGC Printemps', spend: 1920, roas: 1.17, signal: 'OK' },
  ],
  fetched_at: new Date().toISOString(),
  source: 'demo_static',
};
return JSON.stringify(demo, null, 2);"""


def _uid() -> str:
    return str(uuid.uuid4())


def _cred_placeholder(cred_type: str, name: str) -> dict:
    return {"id": _uid(), "name": name}


def _sticky(name: str, content: str, x: float, y: float, w: float = 420, h: float = 280, color: int = 5) -> dict:
    return {
        "parameters": {"content": content, "height": h, "width": w, "color": color},
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [x, y],
        "id": _uid(),
        "name": name,
    }


def build_chat_workflow() -> dict:
    nid = {
        "guide": _uid(),
        "trigger": _uid(),
        "agent": _uid(),
        "anthropic": _uid(),
        "memory": _uid(),
        "tool": _uid(),
        "vector": _uid(),
        "embeddings": _uid(),
        "phase2": _uid(),
    }
    names = {
        "guide": "📋 Guide — Copilote fondateur",
        "trigger": "Quand un message chat arrive",
        "agent": "AI Agent — Copilote SEA",
        "anthropic": "Claude Sonnet — Anthropic",
        "memory": "Mémoire session (12 tours)",
        "tool": "meta_compte_live",
        "vector": "Supabase — search_rapports_meta",
        "embeddings": "Embeddings OpenAI",
        "phase2": "Phase 2 — Supabase",
    }

    nodes = [
        _sticky(
            names["guide"],
            "## SEA Copilot — Agent fondateur\n\n"
            "1. Connecter **Anthropic**, **OpenAI** (embeddings), **Supabase** (optionnel phase 2).\n"
            "2. Exécuter d'abord le workflow **Ingestion** une fois.\n"
            "3. Ouvrir le chat n8n et poser une question sur Lumière Paris.\n"
            "4. L'agent appelle `meta_compte_live` pour les chiffres démo.",
            -680,
            -120,
            w=480,
            h=320,
        ),
        {
            "parameters": {"options": {}},
            "type": "@n8n/n8n-nodes-langchain.chatTrigger",
            "typeVersion": 1.4,
            "position": [0, 300],
            "id": nid["trigger"],
            "name": names["trigger"],
            "webhookId": _uid(),
        },
        {
            "parameters": {
                "promptType": "define",
                "text": "={{ $json.chatInput }}",
                "options": {"systemMessage": SYSTEM_MESSAGE},
            },
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1.7,
            "position": [420, 300],
            "id": nid["agent"],
            "name": names["agent"],
            "continueOnFail": True,
        },
        {
            "parameters": {"model": "claude-sonnet-4-20250514", "options": {}},
            "type": "@n8n/n8n-nodes-langchain.lmChatAnthropic",
            "typeVersion": 1.3,
            "position": [180, 520],
            "id": nid["anthropic"],
            "name": names["anthropic"],
            "credentials": {"anthropicApi": _cred_placeholder("anthropicApi", "Anthropic account")},
        },
        {
            "parameters": {
                "sessionIdType": "customKey",
                "sessionKey": "={{ $json.sessionId }}",
                "contextWindowLength": 12,
            },
            "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
            "typeVersion": 1.3,
            "position": [180, 680],
            "id": nid["memory"],
            "name": names["memory"],
        },
        {
            "parameters": {
                "name": "meta_compte_live",
                "description": "Récupère les métriques Meta Ads actuelles du compte (démo : Lumière Paris — campagnes, ROAS, alertes DÉCROCHE). Appeler avant toute analyse « live ».",
                "language": "javaScript",
                "jsCode": META_TOOL_JS,
            },
            "type": "@n8n/n8n-nodes-langchain.toolCode",
            "typeVersion": 1.1,
            "position": [640, 520],
            "id": nid["tool"],
            "name": names["tool"],
        },
        {
            "parameters": {
                "mode": "retrieveAsTool",
                "toolName": "search_rapports_meta",
                "toolDescription": "Recherche sémantique dans les rapports narratifs Meta archivés (historique client, périodes passées, décisions).",
                "tableName": "narrative_reports",
                "options": {},
            },
            "type": "@n8n/n8n-nodes-langchain.vectorStoreSupabase",
            "typeVersion": 1.1,
            "position": [640, 680],
            "id": nid["vector"],
            "name": names["vector"],
            "credentials": {"supabaseApi": _cred_placeholder("supabaseApi", "Supabase account")},
        },
        {
            "parameters": {"model": "text-embedding-3-small", "options": {}},
            "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi",
            "typeVersion": 1.2,
            "position": [420, 860],
            "id": nid["embeddings"],
            "name": names["embeddings"],
            "credentials": {"openAiApi": _cred_placeholder("openAiApi", "OpenAI account")},
        },
        _sticky(
            names["phase2"],
            "## Phase 2 : activer Supabase\n\n"
            "Sans Supabase : l'agent fonctionne avec **meta_compte_live** + mémoire session.\n\n"
            "Avec Supabase : exécuter `supabase-setup.sql`, lancer **Ingestion**, puis activer les credentials ici.",
            820,
            120,
            w=360,
            h=220,
            color=3,
        ),
    ]

    connections = {
        names["trigger"]: {"main": [[{"node": names["agent"], "type": "main", "index": 0}]]},
        names["anthropic"]: {
            "ai_languageModel": [[{"node": names["agent"], "type": "ai_languageModel", "index": 0}]]
        },
        names["memory"]: {"ai_memory": [[{"node": names["agent"], "type": "ai_memory", "index": 0}]]},
        names["tool"]: {"ai_tool": [[{"node": names["agent"], "type": "ai_tool", "index": 0}]]},
        names["vector"]: {"ai_tool": [[{"node": names["agent"], "type": "ai_tool", "index": 0}]]},
        names["embeddings"]: {
            "ai_embedding": [[{"node": names["vector"], "type": "ai_embedding", "index": 0}]]
        },
    }

    return {
        "name": "SEA Copilot — Agent Fondateur Meta (v1)",
        "nodes": nodes,
        "connections": connections,
        "pinData": {},
        "active": False,
        "settings": {"executionOrder": "v1"},
        "versionId": _uid(),
        "meta": {"templateCredsSetupCompleted": False, "instanceId": _uid()},
        "tags": [],
    }


INGEST_DOCS_CODE = r"""const docs = [
  {
    client: 'Lumière Paris',
    period: '2026-04 — Rapport mensuel',
    content: `# Rapport Meta — Lumière Paris (Avril 2026)\n\n## Synthèse\nROAS compte 3.85. Catalogue dynamique porteur. Panier abandon stable (ROAS 2.4).\n\n## Décision\nMaintenir budget retargeting, test créa UGC sur notoriété.`,
  },
  {
    client: 'Lumière Paris',
    period: '2026-05 — Alertes mi-mois',
    content: `# Point mi-mai — Panier Abandon\n\nCampagne **Retargeting — Panier Abandon 7j** : hausse budget +30%, ROAS passé de 2.45 à 1.18.\n\n**Recommandation archive** : pause partielle ou baisse enchères, message client sur qualité trafic vs volume.`,
  },
  {
    client: 'Lumière Paris',
    period: '2026-05 — Focus fondateur',
    content: `# Narratif rétention\n\nLe fondateur doit montrer qu'il voit la décroche avant le client. Angle : protection marge + plan 48h (créas, exclusions, cap spend).`,
  },
  {
    client: 'Horizon SEA — Interne',
    period: '2026-Q2 — Playbook',
    content: `# Playbook agence\n\nToujours structurer l'analyse en 4 blocs : va bien / décroche / 48h / message client.`,
  },
];

return docs.map((d, i) => ({
  json: {
    text: d.content,
    metadata: { client: d.client, period: d.period, source: 'ingest_demo', doc_index: i },
  },
}));"""


def build_ingest_workflow() -> dict:
    names = {
        "guide": "📋 Guide — Ingestion RAG",
        "manual": "Lancer ingestion manuelle",
        "code": "Préparer rapports démo",
        "loader": "Default Data Loader",
        "splitter": "Recursive Text Splitter",
        "embeddings": "Embeddings OpenAI",
        "vector": "Supabase — INSERT narrative_reports",
    }

    nodes = [
        _sticky(
            names["guide"],
            "## Ingestion rapports → Supabase\n\n"
            "1. Exécuter `supabase-setup.sql` sur votre projet Supabase.\n"
            "2. Configurer credentials OpenAI + Supabase.\n"
            "3. **Exécuter ce workflow une fois** (ou après chaque nouveau rapport).\n"
            "4. Puis utiliser le workflow **Agent Fondateur** (chat).",
            -520,
            80,
            w=440,
            h=260,
        ),
        {
            "parameters": {},
            "type": "n8n-nodes-base.manualTrigger",
            "typeVersion": 1,
            "position": [0, 300],
            "id": _uid(),
            "name": names["manual"],
        },
        {
            "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": INGEST_DOCS_CODE},
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [220, 300],
            "id": _uid(),
            "name": names["code"],
        },
        {
            "parameters": {"jsonMode": "expressionData", "jsonData": "={{ $json.text }}", "options": {}},
            "type": "@n8n/n8n-nodes-langchain.documentDefaultDataLoader",
            "typeVersion": 1,
            "position": [460, 300],
            "id": _uid(),
            "name": names["loader"],
        },
        {
            "parameters": {"chunkSize": 800, "chunkOverlap": 100, "options": {}},
            "type": "@n8n/n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter",
            "typeVersion": 1,
            "position": [460, 480],
            "id": _uid(),
            "name": names["splitter"],
        },
        {
            "parameters": {"model": "text-embedding-3-small", "options": {}},
            "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi",
            "typeVersion": 1.2,
            "position": [700, 480],
            "id": _uid(),
            "name": names["embeddings"],
            "credentials": {"openAiApi": _cred_placeholder("openAiApi", "OpenAI account")},
        },
        {
            "parameters": {
                "mode": "insert",
                "tableName": "narrative_reports",
                "options": {"queryName": "match_narrative_reports"},
            },
            "type": "@n8n/n8n-nodes-langchain.vectorStoreSupabase",
            "typeVersion": 1.1,
            "position": [700, 300],
            "id": _uid(),
            "name": names["vector"],
            "credentials": {"supabaseApi": _cred_placeholder("supabaseApi", "Supabase account")},
        },
    ]

    connections = {
        names["manual"]: {"main": [[{"node": names["code"], "type": "main", "index": 0}]]},
        names["code"]: {"main": [[{"node": names["loader"], "type": "main", "index": 0}]]},
        names["splitter"]: {
            "ai_textSplitter": [[{"node": names["loader"], "type": "ai_textSplitter", "index": 0}]]
        },
        names["embeddings"]: {
            "ai_embedding": [[{"node": names["vector"], "type": "ai_embedding", "index": 0}]]
        },
        names["loader"]: {"ai_document": [[{"node": names["vector"], "type": "ai_document", "index": 0}]]},
    }

    return {
        "name": "SEA Copilot — Ingestion rapports → Supabase Vector",
        "nodes": nodes,
        "connections": connections,
        "pinData": {},
        "active": False,
        "settings": {"executionOrder": "v1"},
        "versionId": _uid(),
        "meta": {"templateCredsSetupCompleted": False, "instanceId": _uid()},
        "tags": [],
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        json.load(f)


def main() -> None:
    chat_path = OUT_DIR / "sea-copilot-chat-v1.json"
    ingest_path = OUT_DIR / "sea-copilot-ingest-v1.json"

    chat = build_chat_workflow()
    ingest = build_ingest_workflow()

    write_json(chat_path, chat)
    write_json(ingest_path, ingest)

    validate(chat_path)
    validate(ingest_path)

    print(f"Wrote {chat_path.name} ({len(chat['nodes'])} nodes)")
    print(f"Wrote {ingest_path.name} ({len(ingest['nodes'])} nodes)")


if __name__ == "__main__":
    main()
