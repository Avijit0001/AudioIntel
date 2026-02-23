from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import Chroma
from langchain.docstore.document import Document

# ----- Embedding model -----
embeddings = OllamaEmbeddings(model="mistral")

# ----- Load embedding-ready text -----
with open("products_embedding.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Split into documents by separator (---)
docs = []
for block in content.split("---"):
    block = block.strip()
    if block:
        docs.append(Document(page_content=block))

# ----- Create Chroma vectorstore -----
vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    persist_directory="chroma_db"
)

vectorstore.persist()

print("Vectorstore created")
