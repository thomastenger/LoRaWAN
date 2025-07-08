#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$POSTGRES_DB" <<-EOSQL
    create extension pg_trgm;
    create extension hstore;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$POSTGRES_DB" <<-EOSQL2
    CREATE TABLE IF NOT EXISTS api_logs (
        id SERIAL PRIMARY KEY,
        user_email TEXT NOT NULL,
        status TEXT DEFAULT 'success',
        endpoint TEXT,
        ip_address TEXT,
        connexion_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
EOSQL2

