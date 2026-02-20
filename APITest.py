from OntologyDriver import OntologyDriver

driver = OntologyDriver("neo4j://127.0.0.1:7687", "neo4j", "08112004")

human = driver.create_class("Human", "Class for human")
writer = driver.create_class("Writer", "class for writer", [human.uri])
height = driver.add_class_attribute(human.uri, "height")
human_name = driver.add_class_attribute(human.uri, "name")

pet = driver.create_class("Pet", "class for pets")

petProperty = driver.add_class_object_attribute(human.uri, "love", pet.uri)

pushkin, (datatypes, objecttypes) = driver.create_object(writer.uri)
driver.update_object_description(pushkin.uri, "Russian writer")
driver.update_object_datatypeProperty(pushkin.uri, "name", "AS Pushkin")
driver.update_object_datatypeProperty(pushkin.uri, "height", 180)

dog, _ = driver.create_object(pet.uri)
driver.update_object_objectProperty(pushkin.uri, "love", "Pet", dog.uri)

driver.delete_class(human.uri)
driver.delete_object(dog.uri)
driver.delete_class(pet.uri)
