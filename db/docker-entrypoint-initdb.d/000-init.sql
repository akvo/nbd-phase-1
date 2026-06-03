DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nbd_user') THEN
        CREATE ROLE nbd_user WITH LOGIN CREATEDB PASSWORD 'password';
    ELSE
        ALTER ROLE nbd_user CREATEDB PASSWORD 'password';
    END IF;
END $$;

SELECT 'CREATE DATABASE nbd_db WITH OWNER = nbd_user TEMPLATE = template0 ENCODING = ''UTF8'' LC_COLLATE = ''en_US.UTF-8'' LC_CTYPE = ''en_US.UTF-8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nbd_db')\gexec

SELECT 'CREATE DATABASE nbd_db_test WITH OWNER = nbd_user TEMPLATE = template0 ENCODING = ''UTF8'' LC_COLLATE = ''en_US.UTF-8'' LC_CTYPE = ''en_US.UTF-8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nbd_db_test')\gexec