# main.py

import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error as MySQLError
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import OpenAIEmbeddings
import logging
import json
from datetime import date
# from vecdata1 import DocumentProcessor  # Import DocumentProcessor from vecdata1
from schema import get_mysql_schema
from DocumentProcessor import DocumentProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
processor=DocumentProcessor()
class QueryProcessor:
    def __init__(self):
        load_dotenv()

        # OpenAI API Key
        self.api_key = os.getenv("OPENAI_API_KEY")

        



        # MySQL Database Configuration
        self.mysql_db_config = {
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "host": os.getenv("MYSQL_HOST"),
            "database": os.getenv("MYSQL_DATABASE")
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
            schema_info, _, _ = get_mysql_schema(self.mysql_db_config)

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
                conn = mysql.connector.connect(**self.mysql_db_config)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql_query)
                results = cursor.fetchall()
                cursor.close()
                conn.close()
            except MySQLError as err:
                logger.error(f"Error executing SQL query: {err}")
            return results
        except Exception as e:
            logger.error(f"Error generating or executing SQL query: {e}")
            raise

    