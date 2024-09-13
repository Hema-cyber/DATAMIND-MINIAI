import os

import time

from pinecone import Pinecone, ServerlessSpec

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, CSVLoader
from dotenv import load_dotenv
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from fastapi import FastAPI

load_dotenv()

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size=1000, chunk_overlap=0):
        self.index_name = os.getenv("INDEX_NAME")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        self.pinecone_client = Pinecone(api_key=self.pinecone_api_key)
        self.path=os.getenv("DATA_DIR_PATH")
        self.pinecone_index = None
        self.docsearch = None
    
    def initialize_pinecone(self):
        pc = self.pinecone_client
        if self.index_name in pc.list_indexes().names():
            index = pc.Index(self.index_name)
            print("Index already exists:", self.index_name)
            print(index.describe_index_stats())
        else:
            pc.create_index(
                name=self.index_name,
                dimension=1536,  # Replace with your model dimensions
                metric="cosine",  # Replace with your model metric
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            while not pc.describe_index(self.index_name).status["ready"]:
                time.sleep(1)
            index = pc.Index(self.index_name)
            print("Index created:", self.index_name)
        return index

   

    def process_documents(self, directory_path):
        pdf_loader = DirectoryLoader(
            path=directory_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        pdf_docs = pdf_loader.load()

        csv_loader = DirectoryLoader(
            path=directory_path,
            glob="**/*.csv",
            loader_cls=CSVLoader
        )
        csv_docs = csv_loader.load()

        docs = pdf_docs + csv_docs
        for doc in docs:
            filename = doc.metadata.get('source', '').split("\\")[-1]
            doc.metadata.update({"filename": filename})

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        documents = text_splitter.split_documents(docs)

        return documents

    def create_or_load_vectorstore(self, documents, docs_already_in_pinecone):
        self.initialize_pinecone()  # Ensure Pinecone is initialized

        if docs_already_in_pinecone.lower() == "y":
            docsearch = PineconeVectorStore(index_name=self.index_name, embedding=self.embeddings)
            print("Existing Vectorstore is loaded")
        elif docs_already_in_pinecone.lower() == "n":
            docsearch = PineconeVectorStore.from_documents(documents, self.embeddings, index_name=self.index_name)
            print("New vectorstore is created and loaded")
        else:
            raise ValueError("Please type 'Y' for yes or 'N' for no")
        # self.docsearch = docsearch
        return docsearch

    
    def retrieve_and_extract(self,user_query, path=""):
        docs = self.process_documents(self.path)
        docsearch = self.create_or_load_vectorstore(docs, "y")


        retriver = docsearch.as_retriever()
        return retriver.invoke(user_query)
    

