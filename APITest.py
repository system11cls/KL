from DBapi import CipherApi, CipherTools

driver = CipherApi("neo4j://127.0.0.1:7687", "neo4j", "neo4j")

print(CipherTools.generate_random_string())
