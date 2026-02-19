from typing import List

from DBapi import CipherApi

class OntologyDriver:

    def __init__(self, host:str, user:str, password:str):
        self.driver = CipherApi(host, user, password)

    def get_ontology(self):
        return self.driver.get_all_nodes_and_arcs()

    def get_ontology_parent_classes(self):
        nodes = self.driver.get_nodes_by_labels(['Class'])
        res = []
        for (node, arcs) in nodes:
            is_sparent = False
            for arc in arcs:
                if arc.label == "subclass":
                    is_sparent = True
                    break
            if is_sparent:
                res.append((node, arcs))
        return res


    def get_class(self, uri:str):
        node = self.driver.get_node_by_uri(uri)
        arcs = self.driver.get_node_arcs(node.uri)
        return (node, arcs)

    def get_class(self, labels: List[str]):
        if labels[0] != "Class":
            labels.insert(0, "Class")
        node = self.driver.get_nodes_by_labels(labels)
        return node

    def get_class_parents(self):



