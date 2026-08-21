from retrieval.retriever import retrieve_evidence


service = "payment-service"

query = (
    "Payment requests are failing with HTTP 500 errors "
    "after a recent deployment."
)


evidence = retrieve_evidence(
    service=service,
    query=query,
    max_evidence=5,
    similarity_threshold=0.45
)


print("\n===== RETRIEVAL TEST =====")
print(f"Service: {service}")
print(f"Query: {query}")
print("==========================\n")


if not evidence:
    print("NO RELEVANT EVIDENCE FOUND")
else:
    for index, item in enumerate(evidence, start=1):
        print(f"--- Evidence {index} ---")
        print(item)
        print()