-- Exécuter avec psql en administrateur PostgreSQL. Ne jamais versionner le mot de passe.
-- Le rôle n'est ni superuser, ni créateur de rôles ou de bases.
CREATE ROLE ihme_suivi LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password ihme_suivi
CREATE DATABASE ihme_suivi OWNER ihme_suivi;
REVOKE ALL ON DATABASE ihme_suivi FROM PUBLIC;
GRANT CONNECT ON DATABASE ihme_suivi TO ihme_suivi;
\connect ihme_suivi
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO ihme_suivi;
