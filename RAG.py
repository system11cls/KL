from statistics import mean

from ollama import chat
from typing import List, Tuple

from DBapi import TNode, TArc
from OntologyDriver import OntologyDriver
from embeddings import EmbeddingsWorker

class RAG:
    __host = "neo4j://localhost:7687"
    __user = "neo4j"
    __password = "08112004"

    def __init__(self):
        self.__driver = OntologyDriver(self.__host, self.__user, self.__password)
        self.__embeddings = EmbeddingsWorker()
        self.__data = self.__init_data(self.__driver.get_ontology())


    def __init_data(self, ontology: List[Tuple[TNode, List[TArc]]]):
        res = {}

        for (node, arcs) in ontology:
            res[node.uri] = [node, arcs]

        for [node, arcs] in ontology:
            curMessage = node.make_message()
            for arc in arcs:
                curMessage += arc.make_message(res[arc.node_uri_to][0].title)
            res[node.uri].append(curMessage)
            res[node.uri].append(self.__embeddings.get_embeddings(self.__embeddings.get_chunks(curMessage)))


        return res


    def __add_messages(self, res:set[str], question:str, tolerance:float = 0.5):
        sentences = self.__embeddings.get_chunks(question)
        sentences_emb = self.__embeddings.get_embeddings(sentences)
        for _, node in self.__data.items():
            if node[2] in res:
                continue
            for sentence_emb in sentences_emb:
                if node[2] in res:
                    break
                for emb in node[3]:
                    if (self.__embeddings.сos_compare(sentence_emb, emb) >= tolerance):
                        res.add(node[2])
                        break

    def __get_answer(self, text, question):
        messages = [
            {"role": "system", "content": f"Текст: {text}"},
            {"role": "user", "content": f"Дай ответ на данный вопрос, используя информацию из текста: {question}"},
        ]

        response = chat(
            model='lakomoor/vikhr-llama-3.2-1b-instruct:q3_k_m',
            messages=messages,
        )

        return response.message.content


    def get_answer(self, question:str, tolerance:float = 0.6):

        res = set()
        self.__add_messages(res, question, tolerance)

        fans = self.__get_answer(res, question)

        self.__add_messages(res, fans, tolerance)

        sans = self.__get_answer(res, question)

        return sans
