import mysql.connector
from mysql.connector import Error as MySQLError

def get_mysql_schema(mysql_db_config):
    schema_info = ""
    table_names = set()
    column_names = set()
    
    try:
        # Establish connection
        with mysql.connector.connect(**mysql_db_config) as conn:
            with conn.cursor(dictionary=True) as cursor:
                # Get table names
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()

                for table in tables:
                    table_name = list(table.values())[0]
                    table_names.add(table_name.lower())
                    schema_info += f"Table: {table_name}\n"
                    
                    # Get columns
                    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                    columns = cursor.fetchall()
                    for column in columns:
                        column_name = column['Field'].lower()
                        column_names.add(column_name)
                        schema_info += f" - {column_name} ({column['Type']})\n"
                    
                    # Get primary keys
                    cursor.execute(f"""
                        SELECT COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_NAME = '{table_name}' AND CONSTRAINT_NAME = 'PRIMARY'
                    """)
                    primary_keys = cursor.fetchall()
                    if primary_keys:
                        schema_info += " - Primary Key:\n"
                        for pk in primary_keys:
                            schema_info += f"   - {pk['COLUMN_NAME'].lower()}\n"

                    # Get foreign keys
                    cursor.execute(f"""
                        SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_NAME = '{table_name}' AND REFERENCED_TABLE_NAME IS NOT NULL
                    """)
                    foreign_keys = cursor.fetchall()
                    if foreign_keys:
                        schema_info += " - Foreign Keys:\n"
                        for fk in foreign_keys:
                            schema_info += f"   - {fk['COLUMN_NAME'].lower()} -> {fk['REFERENCED_TABLE_NAME'].lower()}.{fk['REFERENCED_COLUMN_NAME'].lower()}\n"

                    schema_info += "\n"

    except MySQLError as err:
        print(f"Error: {err}")

    return schema_info, table_names, column_names