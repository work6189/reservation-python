DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'web') THEN
      CREATE ROLE web WITH LOGIN PASSWORD 'postgres_pw';
   END IF;
END
$$;

DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'exam') THEN
      CREATE DATABASE exam;
   END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE exam TO web;

\c exam
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO web;