-- SEA Copilot — Supabase pgvector (n8n quickstart pattern)
-- Exécuter dans le SQL Editor du projet Supabase.

create extension if not exists vector;

create table if not exists narrative_reports (
  id bigserial primary key,
  content text,
  metadata jsonb default '{}'::jsonb,
  embedding vector(1536)
);

create index if not exists narrative_reports_embedding_idx
  on narrative_reports
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Fonction de similarité pour le nœud Supabase Vector Store (mode retrieve / retrieveAsTool)
create or replace function match_narrative_reports (
  query_embedding vector(1536),
  match_count int default 5,
  filter jsonb default '{}'::jsonb
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    narrative_reports.id,
    narrative_reports.content,
    narrative_reports.metadata,
    1 - (narrative_reports.embedding <=> query_embedding) as similarity
  from narrative_reports
  where narrative_reports.metadata @> filter
  order by narrative_reports.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Optionnel : RLS (désactivé par défaut pour démo — activer en prod)
-- alter table narrative_reports enable row level security;
