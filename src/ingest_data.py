import os
import sys
import urllib.parse  
import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import PGVector

# Load environment variables from the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# 1. Safely encode the password to handle @, /, :, etc.
raw_password = os.getenv('POSTGRES_PASSWORD')
if raw_password is None:
    print("[ERROR] POSTGRES_PASSWORD not set. Check your .env file.")
    sys.exit(1)
encoded_password = urllib.parse.quote(raw_password, safe="")

# 2. Use the encoded password in the connection string
CONNECTION_STRING = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:{encoded_password}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'postgres')}"

# This is the 'table' inside our pgvector database where embeddings will live
COLLECTION_NAME = "reddit_sarcasm"

# ... (the rest of your setup_rag_memory function stays exactly the same)

def setup_rag_memory():
    print("1. Loading the cleaned dataset...")
    df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'cleaned_sarcasm.csv'))
    
    # We will slice the dataframe to 500 rows for the initial test run
    # so you aren't waiting 20 minutes to see if it works.
    test_df = df
    
    print(f"2. Converting {len(test_df)} rows into LangChain Documents...")
    documents = []
    for _, row in test_df.iterrows():
        # The 'comment' is the payload. We store the 'parent_comment' as metadata 
        # to retain the original context of the sarcasm.
        doc = Document(
            page_content=str(row['comment']),
            metadata={"parent_context": str(row['parent_comment'])}
        )
        documents.append(doc)

    print("3. Initializing Embedding Model (Downloading weights)...")
    # This model runs perfectly on your CPU and maps text to a 384-dimensional vector
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print("4. Embedding text and inserting into PostgreSQL...")
    # This automatically creates the schema and executes the vector insertions
    db = PGVector.from_documents(
        embedding=embeddings,
        documents=documents,
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        pre_delete_collection=True # Overwrites existing data in this collection
    )
    
    print("[OK] Ingestion complete!")
    
    print("\n--- Testing Retrieval ---")
    query = "I just got a massive promotion at work today!"
    print(f"User says: '{query}'\n")
    
    # Retrieve the top 2 closest vectors based on cosine similarity
    docs_with_score = db.similarity_search_with_score(query, k=2)
    
    for doc, score in docs_with_score:
        # A lower score generally indicates closer proximity in this LangChain wrapper
        print(f"Retrieved Snark (Distance: {score:.4f}): {doc.page_content}")
        print(f"Original Context: {doc.metadata['parent_context']}\n")

if __name__ == "__main__":
    setup_rag_memory()