import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError as PostgresError
from psycopg2 import extras as psycopg2_extras
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import OpenAIEmbeddings
import logging
from postgresql import get_postgres_schema  # Ensure this import is correct

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLProcessor:
    def __init__(self):
        load_dotenv()

        # OpenAI API Key
        self.api_key = os.getenv("OPENAI_API_KEY")

        # PostgreSQL Database Configuration
        self.postgresql_db_config = {
            "user": os.getenv("POSTSQL_USER"),
            "password": os.getenv("POSTSQL_PASSWORD"),
            "host": os.getenv("POSTSQL_HOST"),
            "database": os.getenv("POSTSQL_DATABASE")
        }

        # Initialize the LLM model
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=self.api_key)

        # Define prompts
        self.sql_prompt_template = """
        You are a SQL expert. Given the schema of the database and a natural language request, generate an accurate SQL query. Please provide only the SQL query with no additional text or explanation.

        Database Schema:
        {schema_info}

        Natural Language Request:
        {user_query}

        SQL Query:
        """

        # Initialize LLM Chains
        self.llm_chain_sql = LLMChain(
            prompt=PromptTemplate(input_variables=["schema_info", "user_query"], template=self.sql_prompt_template),
            llm=self.llm
        )

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

    def generate_and_execute_sql_query(self, user_query):
        try:
            # Check if user query contains required terms
            if not any(term in user_query.lower() for term in ["event_amount", "event_expenses"]):
                logger.info("User query does not contain required terms. No SQL query generated.")
                return []

            # Retrieve PostgreSQL schema
            schema_info, _, _ = get_postgres_schema(self.postgresql_db_config)

            # Generate SQL query
            prompt_result = self.llm_chain_sql.run({
                "schema_info": schema_info,
                "user_query": user_query
            })

            sql_query = prompt_result.strip()
            logger.info(f"Generated SQL Query: {sql_query}")

            if not sql_query.lower().startswith("select"):
                raise ValueError("The generated SQL query is not a SELECT query.")

            # Execute SQL query
            results = []
            try:
                conn = psycopg2.connect(**self.postgresql_db_config)
                cursor = conn.cursor(cursor_factory=psycopg2_extras.RealDictCursor)
                cursor.execute(sql_query)
                results = cursor.fetchall()
                cursor.close()
                conn.close()
            except PostgresError as err:
                logger.error(f"Error executing SQL query: {err}")
                raise
            return results
        except Exception as e:
            logger.error(f"Error generating or executing SQL query: {e}")
            raise
