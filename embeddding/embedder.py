# import json
# from langchain_ollama import OllamaEmbeddings
# from langchain_chroma import Chroma
# from langchain_core.documents import Document
# from langchain_text_splitters import RecursiveCharacterTextSplitter

# # -----------------------------
# # CONFIG
# # -----------------------------
# JSON_FILE = "embeddding/products.json"
# PERSIST_DIRECTORY = "./chroma_db"
# COLLECTION_NAME = "products_collection"

# # -----------------------------
# # Convert Product JSON → Documents
# # -----------------------------
# def extract_products(file_path):
#     documents = []

#     with open(file_path, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     for idx, product in enumerate(data):
#         # Convert list fields properly
#         use_cases = ", ".join(product.get("Use Cases", []))

#         text = f"""
#         Product Name: {product.get('product_name', '')}
#         Description: {product.get('description', '')}
#         Type: {product.get('type', '')}
#         Connectivity: {product.get('Connectivity', '')}
#         Price: {product.get('price', '')}
#         Use Cases: {use_cases}
#         """

#         documents.append(
#             Document(
#                 page_content=text.strip(),
#                 metadata={
#                     "source": file_path,
#                     "product_name": product.get("product_name"),
#                     "price": product.get("price"),
#                     "type": product.get("type"),
#                     "connectivity": product.get("Connectivity"),
#                     "url": product.get("url")
#                 }
#             )
#         )

#     return documents


# # -----------------------------
# # Load Products
# # -----------------------------
# all_docs = extract_products(JSON_FILE)
# print(f"Loaded {len(all_docs)} products.")

# if not all_docs:
#     raise ValueError("No documents loaded. Check file paths or JSON structure.")

# # -----------------------------
# # Optional: Split Long Descriptions
# # -----------------------------
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=800,
#     chunk_overlap=100
# )

# split_docs = text_splitter.split_documents(all_docs)
# print(f"After splitting: {len(split_docs)} chunks.")

# # -----------------------------
# # Initialize Ollama Embeddings
# # -----------------------------
# embeddings = OllamaEmbeddings(
#     model="nomic-embed-text:latest"
# )

# # -----------------------------
# # Create Chroma Vectorstore
# # -----------------------------
# vectorstore = Chroma.from_documents(
#     documents=split_docs,
#     embedding=embeddings,
#     persist_directory=PERSIST_DIRECTORY,
#     collection_name=COLLECTION_NAME
# )


# print("✅ ChromaDB vectorstore created successfully!")


import json
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -----------------------------
# CONFIG
# -----------------------------
JSON_FILE = "products.json"
PERSIST_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "products_collection"

# -----------------------------
# Convert Product JSON → Documents
# -----------------------------
def extract_products(file_path):
    documents = []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for product in data:

        text = f"""
        Product Name: {product.get('product_name', '')}
        Description: {product.get('description', '')}
        Price: {product.get('price', '')}
        """

        documents.append(
            Document(
                page_content=text.strip(),
                metadata={
                    "source": file_path,
                    "product_name": product.get("product_name"),
                    "price": product.get("price"),
                    "url": product.get("url")
                }
            )
        )

    return documents


# -----------------------------
# Load Products
# -----------------------------
all_docs = extract_products(JSON_FILE)
print(f"Loaded {len(all_docs)} products.")

if not all_docs:
    raise ValueError("No documents loaded. Check file paths or JSON structure.")

# -----------------------------
# Split Long Descriptions
# -----------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

split_docs = text_splitter.split_documents(all_docs)
print(f"After splitting: {len(split_docs)} chunks.")

# -----------------------------
# Initialize Ollama Embeddings
# -----------------------------
embeddings = OllamaEmbeddings(
    model="nomic-embed-text:latest"
)

# -----------------------------
# Create Chroma Vectorstore
# -----------------------------
vectorstore = Chroma.from_documents(
    documents=split_docs,
    embedding=embeddings,
    persist_directory=PERSIST_DIRECTORY,
    collection_name=COLLECTION_NAME
)

vectorstore.persist()

print("✅ ChromaDB vectorstore created successfully!")

