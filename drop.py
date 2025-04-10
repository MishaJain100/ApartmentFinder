from app import app, db
from sqlalchemy import text

with app.app_context():
    engine = db.engine
    conn = engine.connect()

    print("Dropping all foreign key constraints...")
    drop_constraints_sql = """
    BEGIN
        FOR rec IN (
            SELECT table_name, constraint_name
            FROM user_constraints
            WHERE constraint_type = 'R'
        ) LOOP
            EXECUTE IMMEDIATE 'ALTER TABLE "' || rec.table_name || '" DROP CONSTRAINT "' || rec.constraint_name || '"';
        END LOOP;
    END;
    """

    print("Dropping all tables...")
    drop_tables_sql = """
    BEGIN
    FOR rec IN (
        SELECT table_name
        FROM user_tables
        WHERE table_name NOT LIKE 'V$%' -- exclude views like V$LOGMNR_*
        AND table_name NOT LIKE 'LOGMNR%' -- exclude logminer internal tables
        AND table_name NOT LIKE 'MVIEW%' -- optional: excludes materialized view logs
        AND table_name NOT LIKE 'AQ$%' -- exclude advanced queue tables
        AND table_name NOT LIKE 'DR$%' -- exclude Oracle Text index tables
        AND table_name NOT LIKE '%$%'
        AND table_name NOT LIKE 'REPL_VALID_COMPAT'
        AND table_name NOT LIKE 'REPL_SUPPORT_MATRIX'
        AND table_name NOT LIKE 'SQLPLUS_PRODUCT_PROFILE'
        AND table_name NOT LIKE 'HELP'
    ) LOOP
        EXECUTE IMMEDIATE 'DROP TABLE "' || rec.table_name || '" CASCADE CONSTRAINTS';
    END LOOP;
END;

    """

    try:
        conn.execute(text(drop_constraints_sql))
        print("All foreign key constraints dropped.")
    except Exception as e:
        print("Error dropping constraints:", e)

    try:
        conn.execute(text(drop_tables_sql))
        print("All tables dropped.")
    except Exception as e:
        print("Error dropping tables:", e)
