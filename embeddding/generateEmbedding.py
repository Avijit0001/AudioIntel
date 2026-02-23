import pandas as pd

df = pd.read_csv("products.csv").fillna("")

def to_embedding_block(row):
    return f"""
id: {row['id']}
name: {row['name']}
category: {row['category']}
description: {row['description']}
price: {row['price']}
---
""".strip()

blocks = df.apply(to_embedding_block, axis=1)

with open("products_embedding.txt", "w", encoding="utf-8") as f:
    f.write("\n\n".join(blocks))

print("Embedding file created")
