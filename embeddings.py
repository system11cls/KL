from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from typing import List

logging.basicConfig(level=logging.INFO)

class EmbeddingsWorker:

    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

    def get_chunks (self, text:str, seps:str):
        return text.split(seps)


    def get_embeddings(self, lines: List[str]):
        return self.model.encode(lines)

    def ños_compare(self, first, second):
        return cosine_similarity(first.reshape(1, -1), second.reshape(1, -1))[0]

sentens = ["Simple", "Example"]

worker = EmbeddingsWorker()
emb = worker.get_embeddings(sentens)
print(worker.ños_compare(emb[0], emb[1]))