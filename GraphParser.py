import json

from OntologyDriver import OntologyDriver

classes = {}
objects = {}
datatypes_id_to_name = {}
objectTypes = {}

def setParams(params, node):
    for key, value in params.items():
        if key == "http://www.w3.org/2000/01/rdf-schema#comment":
            node["description"] = value
        elif key == "http://www.w3.org/2000/01/rdf-schema#label":
            node["name"] = value[0][:-3]
        elif key == "uri":
            node["uri"] = value.split('/')[-1]
        else:
            node[key.split('/')[-1]] = value


def setDomains(edge):
    start_node_labels = edge["data"]["start_node"]["data"]["labels"]
    node_uri = edge["data"]["start_node"]["id"].rsplit("/")[-1]

    for label in start_node_labels:
        splitted = label.split('/')[-1]
        if splitted == "owl#DatatypeProperty":
            datatypes_id_to_name[node_uri] = {
            "name": edge["data"]["start_node"]["data"]["http://www.w3.org/2000/01/rdf-schema#label"][0][:-3],
            "class": edge["target"].split("/")[-1]
            }

        elif splitted == "owl#ObjectProperty":
            if node_uri in objectTypes:
                objectTypes[node_uri]["domain"] = edge["target"].split("/")[-1]
            else:
                objectTypes[node_uri] = {"domain": edge["target"].split("/")[-1],
                                         "name": edge["data"]["start_node"]["data"][
                                             "http://www.w3.org/2000/01/rdf-schema#label"][0][:-3]}


def setRanges(edge):
    node_uri = edge["data"]["start_node"]["id"].rsplit("/")[-1]

    if node_uri in objectTypes:
        objectTypes[node_uri]["range"] = edge["target"].split("/")[-1]
    else:
        objectTypes[node_uri] = {"range": edge["target"].split("/")[-1],
                                 "name": edge["data"]["start_node"]["data"][
                                     "http://www.w3.org/2000/01/rdf-schema#label"][0][:-3]}


def setSubClasses(edge):
    subClass = classes[edge["source"].split("/")[-1]]
    parent_uri = edge["target"].split("/")[-1]
    if "parent" in subClass:
        subClass["parent"].append(parent_uri)
    else:
        subClass["parent"] = [parent_uri]

def setObjectTypeProperty(edge):
    uri = edge["data"]["uri"].split("/")[-1]
    source = objects[edge["source"].split("/")[-1]]
    target_uri = edge["target"].split("/")[-1]
    source[uri] = target_uri

def parse():
    with open("graph.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        for node in data["nodes"]:
            newData = {}
            params = node["data"]["params_values"]
            setParams(params, newData)
            labels = node["data"]["labels"]
            for label in labels:
                splitted = label.split('/')
                if len(splitted) != 5:
                    if splitted[-1] == "owl#Class":
                        classes[newData["uri"]] = newData
                    elif splitted[-1] == "owl#NamedIndividual":
                        objects[newData["uri"]] = newData
                    else:
                        newData["parent"] = splitted[-1]

        for edge in data["arcs"]:
            type = edge["data"]["uri"].rsplit("/")[-1]
            if type == "rdf-schema#domain":
                setDomains(edge)
            elif type == "rdf-schema#range":
                setRanges(edge)
            elif type == "rdf-schema#subClassOf":
                setSubClasses(edge)
            elif type == "22-rdf-syntax-ns#type":
                continue
            else:
                setObjectTypeProperty(edge)



if __name__ == "__main__":
    data = parse()
    driver = OntologyDriver("neo4j://localhost:7687", "neo4j", password="08112004")
    for _, tclass in classes.items():
        driver.create_class(tclass["name"], tclass["description"], [], uri=tclass["uri"])

    for _, tclass in classes.items():
        if "parent" in tclass:
            for parent in tclass["parent"]:
                driver.add_class_parent(tclass["uri"], parent)

    for _, tData in datatypes_id_to_name.items():
        driver.add_class_attribute(tData["class"], tData["name"])

    for _, property in objectTypes.items():
        driver.add_class_object_attribute(property["domain"], property["name"], property["range"])

    for _, tobject in objects.items():
        driver.create_object(tobject["parent"], {"title": tobject["name"], "description": tobject["description"]}, {}, tobject["uri"])

    for _, tobject in objects.items():
        for key, param in tobject.items():
            if key == "parent" or key == "name" or key == "description":
                continue
            else:
                prop_uri = key
                if prop_uri in datatypes_id_to_name:
                    driver.update_object_datatypeProperty(tobject["uri"], datatypes_id_to_name[prop_uri]["name"], param)
                elif prop_uri in objectTypes:
                    driver.update_object_objectProperty(tobject["uri"], objectTypes[prop_uri]["name"], classes[objectTypes[prop_uri]["range"]]["name"], param)


