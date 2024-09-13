# main.py

import os
from dotenv import load_dotenv
import logging
import json
from QueryProcessor import QueryProcessor
from DocumentProcessor import DocumentProcessor
from PostgreSQLProcessor import PostgreSQLProcessor
from concurrent.futures import ThreadPoolExecutor
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from decimal import Decimal
from flask import Flask,render_template, request, jsonify, abort, send_file
from flask_cors import CORS
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

class MainProcessor:
    def __init__(self):
        self.query_processor = QueryProcessor()
        self.document_processor = DocumentProcessor()
        self.postgresql_processor = PostgreSQLProcessor()

        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))
        
        self.summary_prompt_template = """
        User Query: {user_query}

        SQL Database Results:
        {sql_results}

        Vector Database Results:
        {vector_results}

        Please provide a concise summary of the information above that addresses the user's query.
        Your summary should be in clear and natural language that is easy for the user to understand.
        """

        self.llm_chain_summary = LLMChain(
            prompt=PromptTemplate(input_variables=["user_query", "sql_results", "vector_results"], template=self.summary_prompt_template),
            llm=self.llm
        )

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def fetch_results(self, user_prompt):
        with ThreadPoolExecutor() as executor:
            sql_future = executor.submit(self.query_processor.generate_and_execute_sql_query, user_prompt)
            vector_future = executor.submit(self.document_processor.retrieve_and_extract, user_prompt)
            postgresql_future = executor.submit(self.postgresql_processor.generate_and_execute_sql_query, user_prompt)

            sql_results = sql_future.result()
            vector_results = vector_future.result()
            postgresql_results = postgresql_future.result()

        return sql_results, vector_results, postgresql_results
    
    def process_query(self, user_prompt):
        try:
            sql_results, vector_results, postgresql_results = self.fetch_results(user_prompt)

            summary = self.llm_chain_summary.run({
                "user_query": user_prompt,
                "sql_results": json.dumps(sql_results, default=MainProcessor.default_serializer, indent=2),
                "vector_results": str(vector_results),
                "postgresql_results": json.dumps(postgresql_results, default=MainProcessor.default_serializer, indent=2)
            })

            return summary

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            abort(500, description=f"An error occurred: {str(e)}")

processor = MainProcessor()

@app.route("/")
def index():
    app.logger.info("Index route accessed")
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def process_query_route():
    try:
        start_time = time.time()
        data = request.json
        user_prompt = data.get("prompt", "")
        result = processor.process_query(user_prompt)
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
        return jsonify({
            "result": result,
            "processing_time_ms": round(processing_time, 2)
        })
    except Exception as e:
        logger.error(f"Error in /query route: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8008, debug=True, use_reloader=False, threaded = True)