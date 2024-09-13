import psycopg2
from psycopg2 import pool, Error as PostgresError

def get_postgres_schema(postgresql_db_config):
    schema_info = ""
    table_names = set()
    column_names = set()
    try:
        conn = psycopg2.connect(**postgresql_db_config)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            table_names.add(table_name.lower())
            schema_info += f"Table: {table_name}\n"
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """)
            columns = cursor.fetchall()
            for column in columns:
                column_names.add(column[0].lower())
                schema_info += f" - {column[0]} ({column[1]})\n"

            # Fetch primary key
            cursor.execute(f"""
                SELECT kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_name = kcu.table_name
                WHERE tc.table_name = '{table_name}' AND tc.constraint_type = 'PRIMARY KEY'
            """)
            primary_keys = cursor.fetchall()
            if primary_keys:
                schema_info += " - Primary Key:\n"
                for pk in primary_keys:
                    schema_info += f"   - {pk[0]}\n"

            # Fetch foreign key relationships
            cursor.execute(f"""
                SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='{table_name}'
            """)
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                schema_info += " - Foreign Keys:\n"
                for fk in foreign_keys:
                    schema_info += f"   - {fk[0]} -> {fk[1]}({fk[2]})\n"

        cursor.close()
        conn.close()
    except PostgresError as err:
        print(f"Error: {err}")

    return schema_info, table_names, column_names