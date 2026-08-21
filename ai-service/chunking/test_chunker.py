from chunker import chunk_text


text = """
Payment service started normally.
Database connection failed several times.
Connection pool became exhausted.
HTTP 500 errors increased significantly.
A deployment of version v2.4.1 happened shortly before the incident.
"""


chunks = chunk_text(
    text,
    chunk_size=10,
    overlap=2
)


for index, chunk in enumerate(chunks, start=1):
    print(f"\n--- Chunk {index} ---")
    print(chunk)