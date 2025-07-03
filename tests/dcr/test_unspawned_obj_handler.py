from test_setup import SetUpOCDCRTest

from ocpa.algo.discovery.oc_dcr.util import DiscoverData, UnspawnedObjHandler
from ocpa.objects.oc_dcr_graph import IN_TOP_GRAPH, OCDCRGraph, Event



class TestUnspawnedObjHandler(SetUpOCDCRTest):
    def setUp(self):
        super().setUp()
        # Nur "Order" ist im spawn_mapping → "Item" wird als unspawned erkannt
        self.spawn_mapping = {
            "Order": "Create Order"
        }
        self.activities_mapping = {
            "Link Item to Order": "Item",
            "Ship Order": "Order",
            "Accept": IN_TOP_GRAPH,
            "Add Item": "Item"
        }
        self.data = DiscoverData(
            ocel=self.ocel,
            spawn_mapping=self.spawn_mapping,
            activities_mapping=self.activities_mapping,
            derived_entities=self.derived_entities
        )
        self.handler = UnspawnedObjHandler(self.data)
        self.handler.create_unspawned_obj_activity_map()

    def test_detects_item_as_unspawned(self):
        self.assertIn("Item", self.handler.unspawned_obj)

    def test_activity_mapping_update(self):
        self.handler.handle_input_mapping()
        for act in ["Add Item", "Link Item to Order"]:
            self.assertEqual(self.data.activities_mapping[act], IN_TOP_GRAPH)

    def test_group_adds_item_as_artificial_object(self):
        oc_dcr = OCDCRGraph()
        for act in ["Add Item", "Link Item to Order"]:
            oc_dcr.add_event(Event(act))
        self.handler.handle_input_mapping()
        oc_dcr = self.handler.group_unspawned_obj_activities(oc_dcr)

        self.assertIn("Item", oc_dcr.objects)
        self.assertEqual(
            {e.activity for e in oc_dcr.objects["Item"].events},
            {"Add Item", "Link Item to Order"}
        )