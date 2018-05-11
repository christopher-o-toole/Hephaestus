from server import Hephaestus

def test_server():
    with Hephaestus() as hephaestus:
        hephaestus.run()
