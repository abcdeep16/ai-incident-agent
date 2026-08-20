from retrieval.retriever import retrieve_evidence


evidence = retrieve_evidence("payment-service")

for item in evidence:
    print(item)