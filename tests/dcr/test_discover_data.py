import unittest

from test_setup import SetUpOCDCRTest, RESULTS_DIR

import os

from ocpa.objects.log.importer.ocel import factory as ocel_import_factory

from ocpa.algo.discovery.oc_dcr.util import DiscoverData, SPAWN, ErrorManager
from ocpa.objects.oc_dcr_graph import IN_TOP_GRAPH, Event


class TestDiscover(SetUpOCDCRTest):

    def test_get_activity_mapping(self):
        self.assertEqual(self.data.get_activity_mapping("Add Item"), SPAWN)
        self.assertEqual(self.data.get_activity_mapping("Ship Order"), "Order")
        self.assertEqual(self.data.get_activity_mapping("Link Item to Order"), "Item")

        e1 = Event(activity="Add Item")
        e2 = Event(activity="Ship Order")
        self.assertEqual(self.data.get_activity_mapping(e1), SPAWN)
        self.assertEqual(self.data.get_activity_mapping(e2), "Order")

    def test_is_spawn_activity(self):
        self.assertTrue(self.data.is_spawn_activity("Add Item"))
        self.assertFalse(self.data.is_spawn_activity("Link Item to Order"))

    def test_is_spawned_obj(self):
        self.assertTrue(self.data.is_spawned_obj("Item"))
        self.assertFalse(self.data.is_spawned_obj("Unknown"))

    def test_is_from_subgraph(self):
        self.assertTrue(self.data.is_from_subgraph("Link Item to Order"))
        self.assertFalse(self.data.is_from_subgraph("Add Item"))
        self.assertFalse(self.data.is_from_subgraph("Accept"))

    def test_is_top_level_activity(self):
        self.assertTrue(self.data.is_top_level_activity("Accept"))
        self.assertFalse(self.data.is_top_level_activity("Link Item to Order"))
        self.assertTrue(self.data.is_top_level_activity("Add Item"))

    def test_is_no_spawn_in_top_level(self):
        self.assertTrue(self.data.is_no_spawn_in_top_level("Accept"))
        self.assertFalse(self.data.is_no_spawn_in_top_level("Add Item"))

    def test_get_spawned_activities_of_obj(self):
        result = self.data.get_spawned_activities_of_obj("Item")
        self.assertEqual(result, {"Link Item to Order"})

    def test_are_derived_entities(self):
        self.assertTrue(self.data.are_derived_entities("Item", "Order"))
        self.assertTrue(self.data.are_derived_entities("Order", "Item"))
        self.assertFalse(self.data.are_derived_entities("Item", "Item"))
        self.assertFalse(self.data.are_derived_entities("Order", "Accept"))

class TestErrorManager(SetUpOCDCRTest):

    def setUp(self):
        self.ocel = ocel_import_factory.apply(os.path.join(RESULTS_DIR, "jsonocel/test_log.jsonocel"))
        self.valid_spawn_mapping = {
            "Order": "Create Order",
            "Item": "Add Item"
        }
        self.valid_activities_mapping = {
            "Link Item to Order": "Item",
            "Ship Order": "Order",
            "Accept": IN_TOP_GRAPH
        }

    def test_invalid_object_type_in_spawn_mapping(self):
        with self.assertRaises(KeyError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping={"UnknownType": "Create Something"},
                activities_mapping=self.valid_activities_mapping,
                derived_entities=[]
            )
            ErrorManager(data).validate()

    def test_invalid_activity_in_spawn_mapping(self):
        with self.assertRaises(KeyError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping={"Order": "NotAnActivity"},
                activities_mapping=self.valid_activities_mapping,
                derived_entities=[]
            )
            ErrorManager(data).validate()

    def test_overlap_spawn_and_activities_mapping(self):
        with self.assertRaises(ValueError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping={"Order": "Create Order"},
                activities_mapping={"Create Order": "Order"},
                derived_entities=[]
            )
            ErrorManager(data).validate()

    def test_invalid_object_type_in_activities_mapping(self):
        with self.assertRaises(KeyError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping=self.valid_spawn_mapping,
                activities_mapping={"Ship Order": "NotARealType"},
                derived_entities=[]
            )
            ErrorManager(data).validate()

    def test_invalid_activity_in_activities_mapping(self):
        with self.assertRaises(KeyError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping=self.valid_spawn_mapping,
                activities_mapping={"NonExistentActivity": "Order"},
                derived_entities=[]
            )
            ErrorManager(data).validate()

    def test_derived_entities_self_reference(self):
        with self.assertRaises(ValueError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping=self.valid_spawn_mapping,
                activities_mapping=self.valid_activities_mapping,
                derived_entities=[("Order", "Order")]
            )
            ErrorManager(data).validate()

    def test_derived_entities_unknown_object_type(self):
        with self.assertRaises(ValueError):
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping=self.valid_spawn_mapping,
                activities_mapping=self.valid_activities_mapping,
                derived_entities=[("Order", "NotARealType")]
            )
            ErrorManager(data).validate()

    def test_unmapped_object_type_logs_warning(self):
        # "Item" is not included in spawn_mapping
        spawn_mapping = {"Order": "Create Order"}
        with self.assertLogs(level="WARNING") as log:
            data = DiscoverData(
                ocel=self.ocel,
                spawn_mapping=spawn_mapping,
                activities_mapping=self.valid_activities_mapping,
                derived_entities=[]
            )
            ErrorManager(data).validate()
            self.assertTrue(any("Object_type 'Item'" in message for message in log.output))

    def test_unmapped_activities_auto_assigned(self):
        # Remove "Accept" from mapping to test fallback
        activities_mapping = {
            "Ship Order": "Order",
            "Link Item to Order": "Item"
        }
        data = DiscoverData(
            ocel=self.ocel,
            spawn_mapping=self.valid_spawn_mapping,
            activities_mapping=activities_mapping,
            derived_entities=[]
        )
        ErrorManager(data).validate()
        # Accept should now be mapped to IN_TOP_GRAPH
        self.assertEqual(data.activities_mapping["Accept"], IN_TOP_GRAPH)

    def test_validation_passes_with_valid_input(self):
        data = DiscoverData(
            ocel=self.ocel,
            spawn_mapping=self.valid_spawn_mapping,
            activities_mapping=self.valid_activities_mapping,
            derived_entities=[("Item", "Order")]
        )
        ErrorManager(data).validate()  # should not raise

if __name__ == '__main__':
    unittest.main()