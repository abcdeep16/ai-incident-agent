from embedder import create_embedding


text = "Database connection failed"

embedding = create_embedding(text)

print("Embedding dimensions:", len(embedding))
print("First 5 values:", embedding[:5])