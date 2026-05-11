from statistics import mean

from openai import OpenAI
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
        self.__model = OpenAI(
            api_key="sk-224b58307e77aa8e8dde5f434bd0509fa5e06a62d9ab3d52120a1a8c73ad65df",
            base_url="https://gatellm.ru/v1"
        )


    def __init_data(self, ontology: List[Tuple[TNode, List[TArc]]]):
        res = {}

        for (node, arcs) in ontology:
            res[node.uri] = [node, arcs]

        for [node, arcs] in ontology:
            curMessage = node.make_message()
            for arc in arcs:
                curMessage += arc.make_message(res[arc.node_uri_to][0].title)
            res[node.uri].append(f'[\n{curMessage}\n]\n')
            res[node.uri].append(self.__embeddings.get_embeddings(self.__embeddings.get_chunks(curMessage)))


        return res


    def __add_messages(self, res:set[str], question:str, tolerance):
        sentences = self.__embeddings.get_chunks(question)
        sentences_emb = self.__embeddings.get_embeddings([sentence for sentence in sentences if sentence != ""])
        for _, node in self.__data.items():
            if node[2] in res:
                continue
            for sentence_emb in sentences_emb:
                if node[2] in res:
                    break
                for emb in node[3]:
                    res_prob = self.__embeddings.сos_compare(sentence_emb, emb)
                    if (res_prob >= tolerance):
                        res.add(node[2])
                        break

    def __get_answer(self, text, question):
        messages = [
            {"role": "user", "content": f"Дай ответ на данный вопрос, используя информацию из текста: {question}\n"
                                        f"Текст: {text}"},
        ]

        response = self.__model.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=messages,
            max_tokens=1024
        )

        return response.choices[0].message.content


    def get_answer(self, question:str, tolerance:float = 0.75):

        res = set()
        self.__add_messages(res, question, tolerance)

        fans = self.__get_answer(res, question)

        self.__add_messages(res, fans, tolerance)

        sans = self.__get_answer(res, question)

        return sans
