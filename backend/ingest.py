import os
import time
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
INDEX_NAME = "owasp-qa"
NAMESPACE = "general-security"  # We put all data here for simplicity
DATA_FOLDER = "./data"          # Create this folder and put your PDFs/TXTs here
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

def ingest_data():
    # 1. Initialize Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Create index if it doesn't exist
    if INDEX_NAME not in [index.name for index in pc.list_indexes()]:
        print(f"Creating index: {INDEX_NAME}...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384, # all-MiniLM-L6-v2 outputs 384 dimensions
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        time.sleep(10) # Wait for index to be ready

    index = pc.Index(INDEX_NAME)

    # 2. Load Embedding Model
    print(f"Loading model: {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # 3. Read Files
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"⚠️ Created '{DATA_FOLDER}' folder. Please put your .txt or .pdf files there and run this script again.")
        return

    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.txt')]
    if not files:
        print(f"⚠️ No .txt files found in {DATA_FOLDER}. Add some files first!")
        return

    print(f"Found {len(files)} files to process.")

    # 4. Process & Upload
    for filename in files:
        file_path = os.path.join(DATA_FOLDER, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Simple chunking (split by paragraphs or rough character count)
        chunks = [text[i:i+500] for i in range(0, len(text), 500)]
        
        vectors = []
        for i, chunk in enumerate(chunks):
            # Create Embedding
            embedding = model.encode(chunk).tolist()
            
            # Prepare Metadata
            metadata = {
                "text": chunk,
                "source": filename,
                "chunk_id": i
            }
            
            # ID format: filename_chunkIndex
            vector_id = f"{filename}_{i}"
            vectors.append((vector_id, embedding, metadata))

        # Upload in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            index.upsert(vectors=batch, namespace=NAMESPACE)
            print(f"Uploaded batch {i//batch_size + 1} for {filename}")

    print("\n✅ Ingestion Complete! Your bot now has knowledge.")

if __name__ == "__main__":
    ingest_data()