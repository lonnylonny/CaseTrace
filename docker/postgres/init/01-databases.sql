-- Run by the official entrypoint with psql on the first empty-volume startup.
-- Read the password from the environment, without command-line interpolation.
\getenv app_password CASETRACE_POSTGRES_PASSWORD
CREATE ROLE casetrace LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    PASSWORD :'app_password';
CREATE DATABASE casetrace OWNER casetrace;
CREATE DATABASE casetrace_test OWNER casetrace;
REVOKE ALL ON DATABASE casetrace FROM PUBLIC;
REVOKE ALL ON DATABASE casetrace_test FROM PUBLIC;
