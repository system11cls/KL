import json
import os
from typing import Set

from OntologyDriver import OntologyDriver

cnt_sentences_windows = 1

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

def get_distance(first_mention, second_mention):
    first_mention_mean = (first_mention["pos_start"] + first_mention["pos_end"]) // 2
    second_mention_mean = (second_mention["pos_start"] + second_mention["pos_end"]) // 2
    return abs(first_mention_mean - second_mention_mean)

def find_closest_connection(node, connection):
    node_mention = node["text_mentions"][0]

    min_distance = -1
    cur_min_mention = None
    for conn_mention in connection["text_mentions"]:
        if cur_min_mention is None or min_distance > get_distance(node_mention, conn_mention):
            min_distance = get_distance(node_mention, conn_mention)
            cur_min_mention = conn_mention

    return cur_min_mention

def find_lower_sentence_start(mention, textIds):
    cnt = 0
    curPos = mention["pos_start"]
    while curPos != -1:
        if not(str(curPos) in textIds):
            curPos -= 1
            continue

        if set(textIds[str(curPos)]) & set("!.?;\n"):
            if cnt >= cnt_sentences_windows:
                curPos += 1
                return curPos
            cnt += 1
        curPos -= 1

    return curPos

def find_upper_sentence_end(mention, textIds):
    cnt = 0
    curPos = mention["pos_start"]
    while True:
        if not(str(curPos) in textIds):
            curPos = (curPos // 1000 + 1) * (1000)
            if not(str(curPos) in textIds):
                break
            continue

        if set(textIds[str(curPos)]) & set("!.?;\n"):
            if cnt >= cnt_sentences_windows + 1:
                return curPos
            cnt += 1
        curPos += 1

    return curPos - 1


def add_text_from_mention(mention, textIds, setOfSentences: Set[str]):
    text = ""
    start = find_lower_sentence_start(mention, textIds)
    end = find_upper_sentence_end(mention, textIds) + 1
    for id in range(start, end):
        if not(str(id) in textIds):
            continue
        text += textIds[str(id)]
        if not(id == end - 1):
            text += " "
    setOfSentences.add(text)

def add_text_by_pos(mention, textIds):
    text = ""
    for id in range(mention["pos_start"], mention["pos_end"] + 1):
        text += textIds[str(id)]
        if id != mention["pos_end"]:
            text += " "
    return text


def parse_file_of_text(file):
    text_entities = {}

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
        textIds = data["textWithIds"]

        for entity in data["entites"]:
            text_mentions = [mention for mention in entity["node"]["data"]["text_mentions"] if mention["markup"] == entity["markup"]]
            node_uri = entity["node_uri"].split("/")[-1]
            inTexts = [f'[{add_text_by_pos(mention, textIds)}]' for  mention in text_mentions]
            text_entities[entity["id"]] = {"text_mentions": text_mentions, "uri": node_uri, "inTextTriplets": [], "inText": inTexts}

        for relation in data["relations"]:
            startNode = text_entities[relation["start"]]
            endNode = text_entities[relation["end"]]
            connection = text_entities[relation["connection"]]

            min_mention = find_closest_connection(endNode, connection)

            sentences = set()

            add_text_from_mention(startNode["text_mentions"][0], textIds, sentences)
            add_text_from_mention(min_mention, textIds, sentences)
            add_text_from_mention(endNode["text_mentions"][0], textIds, sentences)

            relation_text = "{"
            for sentence in sentences:
                relation_text += sentence
            relation_text += "}"

            startNode["inTextTriplets"].append(relation_text)
            endNode["inTextTriplets"].append(relation_text)

    return text_entities

def parse_main(driver):
    data = parse()

    print("main file parsed")

    for _, tclass in classes.items():
        driver.create_class(tclass["name"], tclass["description"], [], uri=tclass["uri"])

    print("classes added")

    for _, tclass in classes.items():
        if "parent" in tclass:
            for parent in tclass["parent"]:
                driver.add_class_parent(tclass["uri"], parent)

    print("classes parents added")

    for _, tData in datatypes_id_to_name.items():
        driver.add_class_attribute(tData["class"], tData["name"])

    print("classes attributes added")

    for _, property in objectTypes.items():
        driver.add_class_object_attribute(property["domain"], property["name"], property["range"])

    print("classes object attributes added")

    for _, tobject in objects.items():
        driver.create_object(tobject["parent"], {"title": tobject["name"], "description": tobject["description"]}, {}, tobject["uri"])

    print("classes objects added")

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

    print("objects attributes added")

def update_objects_with_mentions(driver, file):
    file_data = parse_file_of_text(file)
    print(f'file {file} parsed')
    for _, entity in file_data.items():
        if entity["uri"] in objects:
            driver.update_object_datatypeProperty(entity["uri"], "inText", str(entity["inText"]))
            driver.update_object_datatypeProperty(entity["uri"], "inTextTriplets", str(entity["inTextTriplets"]))

    print("mentions added")


if __name__ == "__main__":
    driver = OntologyDriver("neo4j://localhost:7687", "neo4j", password="08112004")
    parse_main(driver)
    for f in os.listdir("texts"):
        update_objects_with_mentions(driver, os.path.join("texts", f))


