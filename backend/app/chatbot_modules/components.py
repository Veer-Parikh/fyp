import asyncio
import os
import torch
import networkx as nx
# from pinecone import Pinecone, ServerlessSpec
# from sentence_transformers import SentenceTransformer
# from huggingface_hub import hf_hub_download
# from llama_cpp import Llama
from .config import CONFIG

class ComponentManager:
    def __init__(self):
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.llm = None
        self.knowledge_graph = None

    async def initialize_pinecone(self):
        """Initialize Pinecone client and index."""
        if not CONFIG.get("USE_PINECONE"):
            print("⏭️ Pinecone disabled")
            return
        try:
            from pinecone import Pinecone, ServerlessSpec
            self.pc = Pinecone(api_key=CONFIG["PINECONE_API_KEY"])

            if CONFIG["PINECONE_INDEX_NAME"] not in [index.name for index in self.pc.list_indexes()]:
                print(f"Creating new Pinecone index: {CONFIG['PINECONE_INDEX_NAME']}")
                self.pc.create_index(
                    name=CONFIG["PINECONE_INDEX_NAME"],
                    dimension=CONFIG["VECTOR_DIMENSION"],
                    metric="cosine",
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )

            self.index = self.pc.Index(CONFIG["PINECONE_INDEX_NAME"])
            print(" Pinecone initialized")
        except Exception as e:
            print(f" Error initializing Pinecone: {e}")

    async def initialize_embedding_model(self):
            """Initialize the embedding model (downloads automatically if needed)."""
            try:
                # Import here to avoid issues if library is missing
                from sentence_transformers import SentenceTransformer
                
                print(f"📥 Loading embedding model: {CONFIG['EMBEDDING_MODEL_PATH']}...")
                
                # REMOVED the 'if os.path.exists(...)' check.
                # This allows SentenceTransformer to download the model from HuggingFace.
                self.embedding_model = SentenceTransformer(
                    CONFIG["EMBEDDING_MODEL_PATH"],
                    device=CONFIG["DEVICE"]
                )
                self.embedding_model.max_seq_length = 512
                self.embedding_model.eval()
                print("✅ Embedding model loaded successfully")

            except Exception as e:
                print(f"❌ Error loading embedding model: {e}")

    # async def initialize_llm(self):
    #     """Initialize the LLM with GPU optimization if available."""
    #     if not CONFIG.get("USE_LOCAL_LLM"):
    #         print("⏭️ Local LLM disabled (using Gemini)")
    #         return
    #     try:
    #         llm_path = os.path.join(CONFIG["LOCAL_MODEL_DIR"], CONFIG["LLM_FILENAME"])

    #         if not os.path.exists(llm_path):
    #             print(f"Downloading {CONFIG['LLM_FILENAME']}...")
    #             hf_hub_download(
    #                 repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    #                 filename=CONFIG["LLM_FILENAME"],
    #                 local_dir=CONFIG["LOCAL_MODEL_DIR"],
    #                 local_dir_use_symlinks=False
    #             )

    #         self.llm = Llama(
    #             model_path=llm_path,
    #             n_gpu_layers=CONFIG["LLM_GPU_LAYERS"],
    #             n_ctx=CONFIG["LLM_CTX_SIZE"],
    #             n_batch=CONFIG["BATCH_SIZE"],
    #             n_threads=os.cpu_count() // 2 if CONFIG["DEVICE"] == 'cpu' else 0, # Use CONFIG["DEVICE"]
    #             verbose=False
    #         )
    #         print(" LLM loaded")
    #     except Exception as e:
    #         print(f" Error loading LLM: {e}")

    async def initialize_knowledge_graph(self):
        """Initialize the knowledge graph if available."""
        try:
            if os.path.exists(CONFIG["KNOWLEDGE_GRAPH_PATH"]):
                self.knowledge_graph = nx.read_gml(CONFIG["KNOWLEDGE_GRAPH_PATH"])
                print(f"✅ Knowledge Graph loaded with {self.knowledge_graph.number_of_nodes()} nodes")
            else:
                print(f"⚠ Knowledge Graph file not found at: {CONFIG['KNOWLEDGE_GRAPH_PATH']}")
        except Exception as e:
            print(f"❌ Error loading knowledge graph: {e}")

    async def init_all(self):
        """Initialize all components asynchronously."""
        print("Initializing components...")
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.set_float32_matmul_precision('high')

        tasks = [
            self.initialize_pinecone(),
            self.initialize_embedding_model(),
            self.initialize_knowledge_graph()
        ]
        await asyncio.gather(*tasks)
        print("\n All components initialized!\n")