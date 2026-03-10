from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from typing import List
import re

logging.basicConfig(level=logging.INFO)

class EmbeddingsWorker:

    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

    def get_chunks(self, text:str, seps:str="!.?;"):
        pattern = f'[{re.escape(seps)}]'
        return re.split(pattern, text)


    def get_embeddings(self, lines: List[str]):
        return self.model.encode(lines)

    def сos_compare(self, first, second):
        return cosine_similarity(first.reshape(1, -1), second.reshape(1, -1))[0]
