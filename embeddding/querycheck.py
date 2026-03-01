from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")

vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="products_collection"
)

results = vectorstore.similarity_search("wireless earphone for travel", k=3)

for doc in results:
    print(doc.metadata["product_name"])
    print(doc.metadata["url"])
    print("-" * 40)
