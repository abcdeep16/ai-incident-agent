from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


model = SentenceTransformer("all-MiniLM-L6-v2")


texts = [
    "Database connection failed",
    "Payment database became unreachable",
    "The frontend button is not responding"
]


embeddings = model.encode(texts)

similarity = cosine_similarity(
    [embeddings[0]],
    embeddings[1:]
)

print("Similarity to database issue:", similarity[0][0])
print("Similarity to frontend issue:", similarity[0][1])