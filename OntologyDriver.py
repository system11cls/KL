from typing import List, Dict

from DBapi import CipherApi, NoNodeException


class OntologyDriver:

    def __init__(self, host:str, user:str, password:str):
        self.__driver = CipherApi(host, user, password)

    def get_ontology(self):
        return self.__driver.get_all_nodes_and_arcs()

    def get_ontology_parent_classes(self):
        nodes = self.__driver.get_nodes_by_labels(['Class'])
        res = []
        for (node, arcs) in nodes:
            is_sparent = False
            for arc in arcs:
                if arc.label == "subclass":
                    is_sparent = True
                    break
            if not(is_sparent):
                res.append((node, arcs))
        return res

    def get_class(self, uri:str):
        node = self.__driver.get_node_by_uri(uri)
        arcs = self.__driver.get_node_arcs(node.uri)
        return (node, arcs)

    def get_class_children(self, node_uri: str):
        return self.__driver.get_sons_nodes(node_uri, "subclass")

    def get_class_parents(self, node_uri:str):
        return self.__driver.get_parent_nodes(node_uri, "subclass")

    def get_class_objects(self, class_uri:str):
        objects = self.__driver.get_sons_nodes(class_uri, "object")
        return objects

    def update_class(self, class_uri, new_desc:str="", new_title:str=""):
        params = {}
        if new_desc != "":
            params["description"] = new_desc
        if new_title != "":
            params["title"] = new_title

        result = self.__driver.update_node(class_uri, params)
        return result

    def create_class(self, title:str, description:str="", parents_uri:List[str]=[], uri=None):
        node = self.__driver.create_node(["Class"], {"title":title, "description":description}, True, uri)
        for parent in parents_uri:
            self.__driver.create_arc(node.uri, parent, ["subclass"], {})
        return node

    def delete_class(self, class_uri:str):
        subclasses = self.__driver.get_sons_nodes(class_uri, "subclass")
        if len(subclasses) > 0:
            for subclass in subclasses:
                self.delete_class(subclass.uri)

        dataTypes = self.__driver.get_sons_nodes(class_uri, "Property_domain")
        for type in dataTypes:
            self.__driver.delete_node_by_uri(type.uri)
        objectProperties = self.__driver.get_sons_nodes(class_uri, "ObjectProperty_domain")
        for objectProperty in objectProperties:
            self.__driver.delete_node_by_uri(objectProperty.uri)

        objects = self.__driver.get_sons_nodes(class_uri, "object")
        for object in objects:
            self.__driver.delete_node_by_uri(object.uri)

        self.__driver.delete_node_by_uri(class_uri)

    def add_class_attribute(self, class_uri:str, title:str, uri=None):
        dataType = self.__driver.create_node(["DatatypeProperty"], {"title":title}, uri)
        self.__driver.create_arc(dataType.uri, class_uri, ["Property_domain"], {})

    def delete_class_attribute(self, datatype_uri):
        title = self.__driver.get_node_by_uri(datatype_uri).title
        domain = self.__driver.get_parent_nodes(datatype_uri, "Property_domain")
        domain = domain[0]
        self.__driver.delete_node_by_uri(datatype_uri)
        self.__delete_datatypeProperty_from_class(domain.uri, title)

    def __delete_datatypeProperty_from_class(self, class_uri:str, title:str):
        class_node = self.__driver.get_node_by_uri(class_uri)
        for child in self.__driver.get_sons_nodes(class_node.uri, "object"):
            self.__driver.update_node(child.uri, {title:""})
        for subclass in self.__driver.get_sons_nodes(class_uri, "subclass"):
            self.__delete_datatypeProperty_from_class(subclass.uri, title)

    def add_class_object_attribute(self, class_uri: str, attr_name: str, range_class_uri: str, uri:str = None):
        property = self.__driver.create_node(["ObjectProperty"], {"title":attr_name}, uri=uri)
        self.__driver.create_arc(property.uri, class_uri, ["ObjectProperty_domain"], {})
        self.__driver.create_arc(property.uri, range_class_uri, ["Property_range"], {})

    def delete_class_object_attribute(self, object_property_uri: str):
        title = self.__driver.get_node_by_uri(object_property_uri).title
        domain = self.__driver.get_parent_nodes(object_property_uri, "ObjectProperty_domain")
        domain = domain[0]
        self.__driver.delete_node_by_uri(object_property_uri)
        self.__delete_objectProperty_from_class(domain.uri, title)

    def __delete_objectProperty_from_class(self, class_uri: str, title:str):
        for object in self.__driver.get_sons_nodes(class_uri, "object"):
            for arc in self.__driver.get_node_arcs(object.uri):
                if arc.label == title:
                    self.__driver.delete_arc_by_id(arc.uri)
        for subclass in self.__driver.get_sons_nodes(class_uri, "subclass"):
            self.__delete_objectProperty_from_class(subclass.uri, title)

    def add_class_parent(self, parent_uri: str, target_uri: str):
        arc = self.__driver.create_arc(parent_uri, target_uri, ["subclass"], {})
        return arc

    def get_object(self, object_uri:str):
        return self.__driver.get_node_by_uri(object_uri), self.__driver.get_node_arcs(object_uri)

    def delete_object(self, object_uri:str):
        return self.__driver.delete_node_by_uri(object_uri)

    def create_object(self, class_uri:str, datatypes: Dict[str, object], objectTypes: Dict[str, (int, str, str)], uri=None):
        node = self.__driver.create_node(["Object", class_uri], {}, True, uri=uri)
        arc = self.__driver.create_arc(node.uri, class_uri, ["object"], {})
        for key, value in datatypes.items():
            self.update_object_datatypeProperty(node.uri, key, value)

        for key, value in objectTypes.items():
            if value[0] == 1:
                self.update_object_objectProperty(node.uri, key, value[1], value[2])
            else:
                self.update_object_objectProperty(value[2], key, value[1], node.uri)

        return node, self.collect_signature(class_uri)

    def update_object_description(self, node_uri:str, description:str):
        self.__driver.update_node(node_uri, {"description": description})

    def update_object_datatypeProperty(self, node_uri, title, value):
        object_node = self.__driver.get_node_by_uri(node_uri)
        class_uri = self.__get_class_uri_by_object(object_node)
        dataTypes, _ = self.collect_signature(class_uri)
        if not (title in dataTypes) and title != "title" and title != "description" and title != "inText" and title != "inTextTriplets":
            raise Exception(f"title \"{title}\" is not in list of dataProperties")

        self.__driver.update_node(node_uri, {title: value})

    def __get_class_uri_by_object(self, object_node):
        return object_node.label[0] if object_node.label[0] != "Object" and object_node.label[
            0] != object_node.uri else object_node.label[1] if object_node.label[1] != "Object" and object_node.label[
            1] != object_node.uri else object_node.label[2]

    def update_object_objectProperty(self, node_uri, title, range_title, range_uri):
        object_node = self.__driver.get_node_by_uri(node_uri)
        class_uri = self.__get_class_uri_by_object(object_node)
        _, objecttypes = self.collect_signature(class_uri)
        if not((title, range_title) in objecttypes):
            raise Exception(f"title or/and range_title {(title, range_title)} is not in list of properties of {object_node.title}")

        range_node = self.__driver.get_node_by_uri(range_uri)
        if range_node is None:
            raise NoNodeException("No range node")
        if not("Object" in range_node.label):
            raise Exception("range node is not an object")

        self.__driver.create_arc(node_uri, range_uri, [title], {})

    def collect_signature(self, class_uri:str):
        datatypes = []
        objecttypes = []
        for parent in self.get_class_parents(class_uri):
            datas, objects = self.collect_signature(parent.uri)
            datatypes += datas
            objecttypes += objects

        class_datas = self.__driver.get_sons_nodes(class_uri, "Property_domain")
        for data in class_datas:
            datatypes.append(data.title)

        for objectType in self.__driver.get_sons_nodes(class_uri, "ObjectProperty_domain"):
            arc_title = objectType.title
            range_title = self.__driver.get_parent_nodes(objectType.uri, "Property_range")[0].title
            objecttypes.append((arc_title, range_title))
        return datatypes, objecttypes
