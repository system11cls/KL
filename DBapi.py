import json
from neo4j import GraphDatabase
from string import ascii_lowercase, digits
from random import choice
from typing import List, Tuple

class TNode:
    uri:str
    description:str
    label: List[str]
    properties : dict


    def __init__(self, uri:str, desc:str, label: List[str], properties:dict):
        self.uri = uri
        self.description = desc
        self.label = label
        self.properties = properties

    def __str__(self):
        return (f'[node_uri = {self.uri},'
                f'  node_desc = {self.description},'
                f'  node_labels = {self.label},'
                f'  {self.properties}]')

class TArc:
    id: int
    uri: str
    label: str
    node_uri_from: str
    node_uri_to: str
    properties:dict

    def __init__(self, id:int, uri:str, label:str, uri_from:str, uri_to:str, properties:dict):
        self.id = id
        self.uri = uri
        self.label = label
        self.node_uri_from = uri_from
        self.node_uri_to = uri_to
        self.properties = properties

    def __str__(self):
        return f'[id = {self.id}  uri = {self.uri}  label = {self.label}  node_from = {self.node_uri_from} node_to = {self.node_uri_to}  {self.properties}]'


class CipherApi:

    def __init__(self, addr, name, password):
        self.driver = GraphDatabase.driver(addr, auth=(name, password))

    def __del__(self):
        self.driver.close()

    def get_all_nodes_and_arcs(self) -> List[Tuple[TNode, List[TArc]]]:
        return self.__executor(self.__get_all_nodes_and_arcs_func)

    def get_nodes_by_labels(self, labels: List[str]) -> List[TNode]:
        return self.__executor(self.__get_nodes_by_labels_func, labels)

    def  get_node_by_uri(self, uri:str) -> TNode:
        return self.__executor(self.__get_node_by_uri_func, uri)

    def get_node_arcs(self, node_uri:str) -> List[TArc]:
        return self.__executor(self.__get_node_arcs_func, node_uri)

    def create_node(self, labels: List[str], props:dict) -> TNode:
        return self.__executor(self.__create_node_func, labels, props)

    def create_arc(self, uri_from:str, uri_to:str, labels: List[str], props:dict) -> TArc:
        return self.__executor(self.__create_arc_func, uri_from, uri_to, labels, props)

    def delete_node_by_uri(self, node_uri) -> int:
        return self.__executor(self.__delete_node_by_uri_func, node_uri)

    def delete_arc_by_id(self, arc_uri:str) -> int:
        return self.__executor(self.__delete_arc_by_id_func, arc_uri)

    def update_node(self, node_uri: str, params: dict) -> int:
        return self.__executor(self.__update_node_func, node_uri, params)

    def __executor(self, func_to_exec, *args, **kwargs):
        try:
            with self.driver.session() as session:
                return func_to_exec(session, *args, **kwargs)
        except Exception as e:
            print("Query failed:", e)
        finally:
            self.driver.session().close()

    def __get_all_nodes_and_arcs_func(self, session):
        result = session.run("""
        MATCH (n)
        CALL (n) {
            OPTIONAL MATCH (n)-[r]->()
            RETURN r
        }
        RETURN n, collect(r) as relations
        """)

        data = list(result)
        res = []
        for record in data:
            node = CipherTools.collect_node(record["n"])
            arcs = record["relations"]
            arcs_list = []
            for arc in list(arcs):
                arcs_list.append(CipherTools.collect_arc(arc))
            res.append((node, arcs_list))
        return res

    def __get_nodes_by_labels_func(self, session, labels: List[str]):

        label = CipherTools.transform_labels(labels)
        result = session.run(f"""
        MATCH (n{label})
        RETURN n
        """)

        data = list(result)
        res = []
        for record in data:
            res.append(CipherTools.collect_node(record["n"]))
        return res

    def __get_node_by_uri_func(self, session, uri:str):
        result = session.run(f"""
        MATCH (n)
        WHERE elementId(n) = \"{uri}\"
        return n
        """)
        data = result.single()
        if data is None:
            return None
        return CipherTools.collect_node(data["n"])

    def __get_node_arcs_func(self, session, node_uri:str):
        result = session.run(f"""
        OPTIONAL MATCH (n)-[l]-()
        WHERE elementId(n) = \"{node_uri}\"
        RETURN collect(l) as arcs
""")
        data = result.single()
        if data is None:
            return []
        arcs = data["arcs"]
        res = []
        for record in arcs:
            res.append(CipherTools.collect_arc(record))
        return res

    def __create_node_func(self, session, labels: List[str], props:dict):
        label = CipherTools.transform_labels(labels)
        properties = CipherTools.transform_props(props)
        result = session.run(f"""
        CREATE (n{label} {properties})
        RETURN n
        """)
        data = result.single()
        if data is None:
            return None
        return CipherTools.collect_node(data["n"])

    def __create_arc_func(self, session, uri_from:str, uri_to:str, labels: List[str], props:dict):
        label = CipherTools.transform_labels(labels)
        properties = CipherTools.transform_props(props)

        result = session.run(f"""
        MATCH (n), (t)
        WHERE elementId(n) = \"{uri_from}\" AND elementId(t) = \"{uri_to}\"
        CREATE (n)-[l{label} {properties}]->(t)
        RETURN l
        """)
        data = result.single()
        if data is None:
            return None
        return CipherTools.collect_arc(data["l"])

    def __delete_node_by_uri_func(self, session, node_uri):

        result = session.run(f"""
        OPTIONAL MATCH (n)
        WHERE elementId(n) = \"{node_uri}\"
        OPTIONAL MATCH (n)-[l]-()
        DETACH DELETE n, l
        RETURN COUNT(n) as deleted
""")
        data = result.single()
        return data["deleted"]

    def __delete_arc_by_id_func(self, session, arc_uri:str):

        result = session.run(f"""
        OPTIONAL MATCH ()-[l]->()
        WHERE elementId(l) = \"{arc_uri}\"
        DELETE l
        RETURN COUNT(l) as deleted
""")
        data = result.single()
        return data["deleted"]

    def __update_node_func(self, session, node_uri: str, params: dict):

        pairs = []
        for key, value in params.items():
            pairs.append(f'n.{key}="{value}"')
        properties = ", ".join(pairs)


        result = session.run(f"""
        MATCH (n)
        WHERE elementId(n) = \"{node_uri}\"
        SET {properties}
        RETURN "Ok" as status
""")
        data = result.single()
        if data is None:
            return None
        return "OK"

class CipherTools:

    @staticmethod
    def generate_random_string(length=64):
        letters = ascii_lowercase + digits + "_-!:"
        return ''.join(choice(letters) for i in range(length))

    @staticmethod
    def collect_node(node):
        name = node.element_id
        description = ""
        if node["description"]:
            description = node["description"]
        label = list(node.labels)
        return TNode(name, description, label, dict(node))

    @staticmethod
    def collect_arc(arc):
        id = arc.id
        uri = arc.element_id
        nodes = arc.nodes
        label = arc.type
        uri_from = nodes[0].element_id
        uri_to = nodes[1].element_id
        return TArc(id, uri, label, uri_from, uri_to, dict(arc))




    @staticmethod
    def transform_labels(labels, separator=':'):
        if len(labels) == 0:
            return '``'
        res = ':'
        for l in labels:
            i = '`{l}`'.format(l=l) + separator
            res += i
        return res[:-1]

    @staticmethod
    def transform_props(props):
        if len(props) == 0:
            return ''
        data = "{"
        for p in props:
            temp = "`{p}`".format(p=p)
            temp += ':'
            temp += "{val}".format(val=json.dumps(props[p]))
            data += temp + ','
        data = data[:-1]
        data += "}"
        return data

