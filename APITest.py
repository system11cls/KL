from embeddings import EmbeddingsWorker

worker = EmbeddingsWorker()
sentens = worker.get_chunks("Simple. Example")
emb = worker.get_embeddings(sentens)
print(worker.сos_compare(emb[0], emb[1]))