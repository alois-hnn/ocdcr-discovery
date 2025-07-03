from ocpa.algo.discovery.oc_dcr.util import DiscoverLogic, ManyToManyDiscovery
from ocpa.objects.log.importer.ocel import factory as ocel_import_factory
from test_setup import SetUpOCDCRTest, RESULTS_DIR

from datetime import datetime
from typing import Dict, Set

from ocpa.algo.discovery.oc_dcr.util import InitialDiscovery
from ocpa.objects.oc_dcr_graph import DCRRelation

import unittest
from unittest.mock import MagicMock
import polars as pl
from ocpa.objects.oc_dcr_graph import OCDCRGraph, OCDCRRelation, RelationTyps, Event, DCRGraph
from ocpa.objects.oc_dcr_graph import IN_TOP_GRAPH

import os

class TestInitialDiscovery(SetUpOCDCRTest):

    def setUp(self):
        super().setUp()
        self.discoverer = InitialDiscovery(self.data)

    def test_extract_object_traces_matches_expected_dataframe(self):
        actual_df = self.discoverer.extract_object_traces()

        expected_rows = [
            {"case:concept:name": "O1", "concept:name": "Create Order",
             "time:timestamp": datetime(2024, 1, 1, 9, 0, 0)},
            {"case:concept:name": "O1", "concept:name": "Link Item to Order",
             "time:timestamp": datetime(2024, 1, 1, 9, 6, 0)},
            {"case:concept:name": "O1", "concept:name": "Ship Order", "time:timestamp": datetime(2024, 1, 1, 10, 0, 0)},
            {"case:concept:name": "O2", "concept:name": "Create Order",
             "time:timestamp": datetime(2024, 1, 1, 11, 0, 0)},
            {"case:concept:name": "O2", "concept:name": "Link Item to Order",
             "time:timestamp": datetime(2024, 1, 1, 11, 11, 0)},
            {"case:concept:name": "O2", "concept:name": "Ship Order", "time:timestamp": datetime(2024, 1, 1, 12, 0, 0)},
            {"case:concept:name": "O2", "concept:name": "Accept", "time:timestamp": datetime(2024, 1, 1, 12, 10, 0)},
            {"case:concept:name": "I1", "concept:name": "Add Item", "time:timestamp": datetime(2024, 1, 1, 9, 5, 0)},
            {"case:concept:name": "I1", "concept:name": "Link Item to Order",
             "time:timestamp": datetime(2024, 1, 1, 9, 6, 0)},
            {"case:concept:name": "I2", "concept:name": "Add Item", "time:timestamp": datetime(2024, 1, 1, 11, 10, 0)},
            {"case:concept:name": "I2", "concept:name": "Link Item to Order",
             "time:timestamp": datetime(2024, 1, 1, 11, 11, 0)},
        ]

        self.help_test_eventlog(expected_rows,actual_df)

    def test_adds_missing_activities(self):
        dcr = DCRGraph()

        # Simuliere DCR-Mining, bei dem nur ein Teil der Aktivitäten enthalten ist
        dcr.add_event("Create Order")
        dcr.add_event("Add Item")

        # Sicherstellen, dass "Ship Order", "Link Item to Order", "Accept" fehlen
        pre_activities = {e.activity for e in dcr.events}
        self.assertNotIn("Ship Order", pre_activities)
        self.assertNotIn("Link Item to Order", pre_activities)
        self.assertNotIn("Accept", pre_activities)

        # Wende Methode an
        updated_dcr = self.discoverer.handle_activities_with_zero_constraints(dcr)

        # Überprüfe, ob nun alle Aktivitäten vorhanden sind
        final_activities = {e.activity for e in updated_dcr.events}
        for expected_activity in self.data.get_activities():
            self.assertIn(expected_activity, final_activities)




    def test_ocdcr_graph_structure(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)
        oc_dcr = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        # test if translate to oc_dcr has the right structure
        self.assertIsInstance(oc_dcr, OCDCRGraph)
        self.assertGreater(len(oc_dcr.events), 0, "No events in OCDCR graph.")
        self.assertGreater(len(oc_dcr.relations), 0, "No relations in OCDCR graph.")
        self.assertGreater(len(oc_dcr.objects), 0, "No objects in OCDCR graph.")

        for obj in oc_dcr.objects:
            self.assertIn(obj, self.data.ocel.object_types)

    def test_exclude_relation_removed(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)
        oc_dcr = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        excluded = set()
        for rel in oc_dcr.relations:
            if rel.start_event.activity == "Create Order" and rel.target_event.activity == "Add Item":
                excluded.add(rel)

        for rel in oc_dcr.relations:
            if rel.start_event.activity == "Add item" and rel.target_event.activity == "Ship Order":
                excluded.add(rel)

        self.assertEqual(len(excluded), 0, "agnostic relation are not removed.")

    def test_cross_object_relation_removed(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)

        # Add manual cross-object relation
        link_item_event = next(e for e in mined_dcr.events if e.activity == "Link Item to Order")
        ship_order_event = next(e for e in mined_dcr.events if e.activity == "Ship Order")

        cross_relation = DCRRelation(start_event=link_item_event, target_event=ship_order_event, type=RelationTyps.C)
        mined_dcr.relations.add(cross_relation)

        # Now handed over to Translator
        oc_dcr = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        # Check whether the cross-relation has been removed
        still_exists = any(
            rel.start_event.activity == "Link Item to Order" and
            rel.target_event.activity == "Ship Order" and
            rel.type.value == RelationTyps.C.value
            for rel in oc_dcr.relations
        )
        self.assertFalse(still_exists, "Cross-object relation was not removed from OC-DCR.")

    def test_top_to_subgraph_relations_have_quantifiers(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)
        oc_dcr: OCDCRGraph = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        violations = []

        for rel in oc_dcr.relations:
            src = oc_dcr.activityToObject.get(rel.start_event, IN_TOP_GRAPH)
            tgt = oc_dcr.activityToObject.get(rel.target_event, IN_TOP_GRAPH)

            # Check: sublevel top level relation
            if (src == IN_TOP_GRAPH) ^ (tgt == IN_TOP_GRAPH):
                qh, qt = rel.get_quantifiers()
                # wrong if no quantifier or many to many
                if not (qh or qt) or (qh and qt):
                    violations.append(rel)

        self.assertEqual(
            len(violations), 0,
            f"Expected one-to-many quantifiers missing in: {violations}"
        )

    def test_top_level_activities_have_no_quantifiers(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)
        oc_dcr: OCDCRGraph = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        violations = []

        for rel in oc_dcr.relations:
            src = oc_dcr.activityToObject.get(rel.start_event, IN_TOP_GRAPH)
            tgt = oc_dcr.activityToObject.get(rel.target_event, IN_TOP_GRAPH)

            #check if the quantifier are aligned right
            if src == IN_TOP_GRAPH:
                qh, qt = rel.get_quantifiers()
                if qh:
                    violations.append(rel)
            elif tgt == IN_TOP_GRAPH:
                qh, qt = rel.get_quantifiers()
                if qt:
                    violations.append(rel)
        self.assertEqual(
            len(violations), 0,
            f"Top-level relations must not have quantifiers: {violations}"
        )

    def test_no_relation_between_spawn_and_spawned_activities(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)
        oc_dcr: OCDCRGraph = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        violations = []

        for obj_type, spawn_act in self.data.spawn_mapping.items():
            spawned_acts = self.data.get_spawned_activities_of_obj(obj_type)

            for rel in oc_dcr.relations:
                sa = rel.start_event.activity
                ta = rel.target_event.activity

                if (sa == spawn_act and ta in spawned_acts) or (ta == spawn_act and sa in spawned_acts):
                    violations.append(rel)

        self.assertEqual(
            len(violations), 0,
            f"Forbidden spawn-to-subgraph relations found: {violations}"
        )

    def test_spawn_events_correctly_assigned(self):
        flat_log = self.discoverer.extract_object_traces()
        mined_dcr = self.discoverer.apply_dcr_discover(flat_log)
        oc_dcr: OCDCRGraph = self.discoverer.translate_to_basic_ocgraph_structure(mined_dcr)

        violations = []

        for obj_type, spawn_act in self.data.spawn_mapping.items():
            try:
                actual_spawn = oc_dcr.objects[obj_type].spawn.activity
                if actual_spawn != spawn_act:
                    violations.append((obj_type, actual_spawn, spawn_act))
            except KeyError:
                violations.append((obj_type, "missing", spawn_act))

        self.assertEqual(
            len(violations), 0,
            f"Spawn events misassigned or missing: {violations}"
        )


class TestToRelations(unittest.TestCase):

    def setUp(self):
        # Setup a DiscoverLogic instance
        self.logic = ManyToManyDiscovery(data=None)

        # Mock OC_DCR graph
        self.mock_oc_dcr = MagicMock()

        # Example mock event mappings
        self.mock_oc_dcr.get_event.side_effect = lambda x: f"event_{x}"

    def test_to_relations_conditions(self):
        relations: Dict[str, Set[str]] = {
            'target1': {'source1', 'source2'},
            'target2': {'source3'}
        }

        result = self.logic._to_relations(relations, RelationTyps.C, self.mock_oc_dcr)

        expected = {
            OCDCRRelation("event_source1", "event_target1", RelationTyps.C, True, True),
            OCDCRRelation("event_source2", "event_target1", RelationTyps.C, True, True),
            OCDCRRelation("event_source3", "event_target2", RelationTyps.C, True, True)
        }

        self.assertEqual(result, expected)

    def test_to_relations_responses(self):
        relations: Dict[str, Set[str]] = {
            'source1': {'target1'},
            'source2': {'target2', 'target3'}
        }

        result = self.logic._to_relations(relations, RelationTyps.R, self.mock_oc_dcr)

        expected = {
            OCDCRRelation("event_source1", "event_target1", RelationTyps.R, True, True),
            OCDCRRelation("event_source2", "event_target2", RelationTyps.R, True, True),
            OCDCRRelation("event_source2", "event_target3", RelationTyps.R, True, True)
        }

        self.assertEqual(result, expected)


class TestFindConditionsResponses(unittest.TestCase):

    def setUp(self):
        # Create mock DiscoverData and ManyToManyDiscovery instance
        self.data_mock = MagicMock()
        self.data_mock.is_from_subgraph.side_effect = lambda x: x.startswith("spawned")
        self.data_mock.spawn_mapping = {"O": "spawn_event"}
        self.data_mock.get_spawned_activities_of_obj.return_value = {"spawned_A", "spawned_B"}

        self.logic = ManyToManyDiscovery(self.data_mock)

        # Mock OCDCRGraph
        self.oc_dcr = MagicMock()
        self.oc_dcr.get_event.side_effect = lambda x: Event(x)

    def test_find_conditions_responses_adds_expected_relations(self):
        # Simulate Polars DataFrame with 1 closure
        log_data = [
            {"case:concept:name": "closure_0", "concept:name": "spawn_event", "time:timestamp": 1, "object_id": "o1"},
            {"case:concept:name": "closure_0", "concept:name": "spawned_A", "time:timestamp": 2, "object_id": "o1"},
            {"case:concept:name": "closure_0", "concept:name": "spawned_B", "time:timestamp": 3, "object_id": "o1"},
        ]
        df = pl.DataFrame(log_data).sort(["case:concept:name", "time:timestamp"])

        self.logic.find_conditions_responses(df, self.oc_dcr)

        args_list = self.oc_dcr.partition.call_args_list

        # Collect relations passed in
        all_relations = set()
        for call in args_list:
            relations = call[0][0] 
            all_relations.update(relations)

        self.assertGreater(len(relations), 0)

        


class TestAllSpawnedInstancesInList(unittest.TestCase):

    def setUp(self):
        self.logic = ManyToManyDiscovery(data=None)

    def test_all_instances_present(self):
        activity = "A"
        event_list = [
            {"concept:name": "A", "object_id": "o1"},
            {"concept:name": "A", "object_id": "o2"},
            {"concept:name": "B", "object_id": "o3"},
        ]
        spawned_objs = {"o1", "o2"}
        self.assertTrue(self.logic._all_spawned_instances_in_list(activity, event_list, spawned_objs))

    def test_missing_instance(self):
        activity = "A"
        event_list = [
            {"concept:name": "A", "object_id": "o1"},
            {"concept:name": "B", "object_id": "o2"},
        ]
        spawned_objs = {"o1", "o2"}
        self.assertFalse(self.logic._all_spawned_instances_in_list(activity, event_list, spawned_objs))

    def test_empty_spawned_objs(self):
        activity = "A"
        event_list = []
        spawned_objs = set()
        self.assertTrue(self.logic._all_spawned_instances_in_list(activity, event_list, spawned_objs))


class TestTrackSpawnedActivities(unittest.TestCase):

    def setUp(self):
        self.data_mock = MagicMock()
        self.data_mock.spawn_mapping = {"Order": "spawn_order"}
        self.data_mock.ocel.obj.raw.objects = {
            "o1": MagicMock(type="Order")
        }
        self.data_mock.get_spawned_activities_of_obj.return_value = {"A", "B"}

        self.logic = ManyToManyDiscovery(self.data_mock)

    def test_track_spawned_activities_adds_to_dict(self):
        spawned_objects = {"A": set(), "B": set()}
        event = {"object_id": "o1"}
        self.logic._track_spawned_activities("spawn_order", event, spawned_objects)

        self.assertEqual(spawned_objects["A"], {"o1"})
        self.assertEqual(spawned_objects["B"], {"o1"})


class TestProcessTraces(unittest.TestCase):

    def setUp(self):
        self.data_mock = MagicMock()
        self.data_mock.spawn_mapping = {"Order": "spawn_order"}
        self.data_mock.is_from_subgraph.side_effect = lambda x: x.startswith("spawned")
        self.data_mock.get_spawned_activities_of_obj.return_value = {"spawned_A", "spawned_B"}
        self.data_mock.ocel.obj.raw.objects = {
            "o1": MagicMock(type="Order")
        }

        self.logic = ManyToManyDiscovery(self.data_mock)

    def test_process_traces_filters_constraints(self):
        # trace where "spawn_order" spawns "spawned_A", then "spawned_B" follows
        log_data = [
            {"case:concept:name": "case1", "concept:name": "spawn_order", "time:timestamp": 1, "object_id": "o1"},
            {"case:concept:name": "case1", "concept:name": "spawned_A", "time:timestamp": 2, "object_id": "o1"},
            {"case:concept:name": "case1", "concept:name": "spawned_B", "time:timestamp": 3, "object_id": "o1"},
        ]
        df = pl.DataFrame(log_data)

        sync_conditions = {"spawned_A": {"spawned_B"}, "spawned_B": {"spawned_A"}}
        sync_responses = {"spawned_A": {"spawned_B"}, "spawned_B": {"spawned_A"}}
        all_activities = {"spawned_A", "spawned_B", "spawn_order"}

        self.logic._process_traces(sync_conditions, sync_responses, all_activities, df)

        # "spawned_A" occurs before "spawned_B", but not the other way, only one condition should remain
        self.assertIn("spawned_A", sync_conditions)
        self.assertEqual(sync_conditions["spawned_B"], {"spawned_A"})  # "A" before "B"
        self.assertEqual(sync_responses["spawned_A"], {"spawned_B"})  # "B" after "A"
        self.assertEqual(sync_responses["spawned_B"], set())  # No B after B


class TestDiscoverLogic(SetUpOCDCRTest):

    def setUp(self):
        super().setUp()
        self.discoverer = DiscoverLogic(data=self.data)

    def test_get_correlated_obj_types_and_related_activities(self):
        corr = self.discoverer.get_correlated_obj_types("Add Item")
        self.assertIn("Item", corr)
        self.assertNotIn("Order", corr)

        corr2 = self.discoverer.get_correlated_obj_types("Ship Order")
        self.assertIn("Order", corr2)

        self.assertTrue(self.discoverer.are_related_activities("Ship Order", "Link Item to Order"))
        self.assertFalse(self.discoverer.are_related_activities("Add Item", "Accept"))

    def test_is_spawned_activity(self):
        obj_id = next(iter(self.data.ocel.obj.raw.objects.keys()))
        object_type = self.data.ocel.obj.raw.objects[obj_id].type

        if object_type in self.spawn_mapping:
            spawned_acts = self.data.get_spawned_activities_of_obj(object_type)
            for act in spawned_acts:
                self.assertTrue(self.discoverer._is_spawned_activity(obj_id, act))


class TestClosures(SetUpOCDCRTest):

    def setUp(self):
        super().setUp()
        self.logic = ManyToManyDiscovery(self.data)

    def test_flattening_of_the_ekg(self):
        actual_df = self.logic.log_from_closures()

        expected_rows = [
            {"case:concept:name": "closure_0", "concept:name": "Create Order",
             "time:timestamp": datetime(2024, 1, 1, 9, 0, 0), "object_id": "O1"},
            {"case:concept:name": "closure_0", "concept:name": "Add Item",
             "time:timestamp": datetime(2024, 1, 1, 9, 5, 0), "object_id": "I1"},
            {"case:concept:name": "closure_0", "concept:name": "Link Item to Order",
             "time:timestamp": datetime(2024, 1, 1, 9, 6, 0), "object_id": "I1"},
            {"case:concept:name": "closure_0", "concept:name": "Ship Order",
             "time:timestamp": datetime(2024, 1, 1, 10, 0, 0), "object_id": "O1"},
            {"case:concept:name": "closure_1", "concept:name": "Create Order",
             "time:timestamp": datetime(2024, 1, 1, 11, 0, 0), "object_id": "O2"},
            {"case:concept:name": "closure_1", "concept:name": "Add Item",
             "time:timestamp": datetime(2024, 1, 1, 11, 10, 0), "object_id": "I2"},
            {"case:concept:name": "closure_1", "concept:name": "Link Item to Order",
             "time:timestamp": datetime(2024, 1, 1, 11, 11, 0), "object_id": "I2"},
            {"case:concept:name": "closure_1", "concept:name": "Ship Order",
             "time:timestamp": datetime(2024, 1, 1, 12, 0, 0), "object_id": "O2"},
            {"case:concept:name": "closure_1", "concept:name": "Accept",
             "time:timestamp": datetime(2024, 1, 1, 12, 10, 0), "object_id": "O2"},
        ]
        self.help_test_eventlog(expected_rows, actual_df)

    def test_empty_closures_edge_case(self):
        self.data.ocel = ocel_import_factory.apply(os.path.join(RESULTS_DIR, "jsonocel/test_log_edge_case_no_closures.jsonocel"))
        result = self.logic.log_from_closures()
        self.assertEqual(result, None)

if __name__ == '__main__':
    unittest.main()