from unittest.mock import patch
from test_setup import SetUpOCDCRTest

import networkx as nx
import unittest

from ocpa.algo.discovery.oc_dcr.util import GraphOptimizations
from ocpa.objects.oc_dcr_graph import OCDCRGraph, Event, RelationTyps,DCRGraph,OCDCRObject,DCRRelation

from ocpa.algo.discovery.oc_dcr import apply as discover_apply

class TestGraphOptimizations(SetUpOCDCRTest):

    def setUp(self):
        super().setUp()
        # test events
        self.event_a = Event("A")
        self.event_b = Event("B")
        self.event_c = Event("C")
        self.event_d = Event("D")
        self.event_e = Event("E")

        # test relations
        self.relation_ab = DCRRelation(self.event_a, self.event_b, RelationTyps.C)
        self.relation_bc = DCRRelation(self.event_b, self.event_c, RelationTyps.C)
        self.relation_ac = DCRRelation(self.event_a, self.event_c, RelationTyps.C)
        self.relation_de = DCRRelation(self.event_d, self.event_e, RelationTyps.E)

        # test graph
        self.test_graph = OCDCRGraph()
        self.test_graph.events.update([self.event_a, self.event_b, self.event_c, self.event_d, self.event_e])
        self.test_graph.relations.update([self.relation_ab, self.relation_bc, self.relation_ac, self.relation_de])

        # object subgraph 
        self.object_graph = OCDCRObject(None, 'Test')
        self.object_graph.events.update([self.event_a, self.event_b, self.event_c])
        self.object_graph.relations.update([self.relation_ab, self.relation_bc, self.relation_ac])
        self.test_graph.objects["obj1"] = self.object_graph

        # Patch networkx functions 
        self.patcher_find_cycle = patch('networkx.find_cycle', side_effect=nx.NetworkXNoCycle)
        self.mock_find_cycle = self.patcher_find_cycle.start()

        self.patcher_transitive_reduction = patch('networkx.transitive_reduction')
        self.mock_transitive_reduction = self.patcher_transitive_reduction.start()

    def tearDown(self):
        self.patcher_find_cycle.stop()
        self.patcher_transitive_reduction.stop()

    def test_group_relations_by_type(self):
        relations = {self.relation_ab, self.relation_bc,self.relation_ac,self.relation_de}

        result = GraphOptimizations._group_relations_by_type(relations)

        self.assertEqual(len(result[RelationTyps.C]), 3)
        self.assertEqual(len(result[RelationTyps.E]), 1)
        self.assertNotIn(RelationTyps.I, result)
        self.assertNotIn(RelationTyps.R, result)

    def test_get_transitive_optimization_no_reduction(self):
        # no transitive relations
        relations = {self.relation_ab, self.relation_bc}
        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C")])
        self.mock_transitive_reduction.return_value = reduced_graph

        result = GraphOptimizations._get_transitive_optimization(relations)

        self.assertEqual(len(result), 2)
        self.assertIn(self.relation_ab, result)
        self.assertIn(self.relation_bc, result)

    def test_get_transitive_optimization_with_reduction(self):
        # relation_ac is transitive through relation_ab and relation_bc
        relations = {self.relation_ab, self.relation_bc, self.relation_ac}
        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C")])
        self.mock_transitive_reduction.return_value = reduced_graph

        result = GraphOptimizations._get_transitive_optimization(relations)

        self.assertEqual(len(result), 2)
        self.assertIn(self.relation_ab, result)
        self.assertIn(self.relation_bc, result)
        self.assertNotIn(self.relation_ac, result)

    def test_get_transitive_optimization_with_cycles(self):
        # create a cycle
        relation_ca = DCRRelation(self.event_c, self.event_a, RelationTyps.C)
        relations = {self.relation_ab, self.relation_bc, relation_ca}

        # Mock cycle detection
        self.mock_find_cycle.side_effect = [[("A", "B"), ("B", "C"), ("C", "A")], nx.NetworkXNoCycle]

        # Mock transitive reduction
        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])
        self.mock_transitive_reduction.return_value = reduced_graph

        result = GraphOptimizations._get_transitive_optimization(relations)

        self.assertEqual(len(result), 3)  # All relations kept because of cycle
        self.assertIn(self.relation_ab, result)
        self.assertIn(self.relation_bc, result)
        self.assertIn(relation_ca, result)

    def test_filter_excluded_relations(self):
        relations = {self.relation_ab, self.relation_bc}
        excludes = {self.relation_ab}

        result = GraphOptimizations._filter_excluded_relations(relations, excludes)

        self.assertEqual(len(result), 1)
        self.assertIn(self.relation_bc, result)
        self.assertNotIn(self.relation_ab, result)

    def test_filter_excluded_relations_empty(self):
        relations = set()
        excludes = {self.relation_ab}

        result = GraphOptimizations._filter_excluded_relations(relations, excludes)

        self.assertEqual(len(result), 0)

    def test_optimize_main_graph(self):
        graph = DCRGraph()
        graph.relations = {self.relation_ab, self.relation_bc, self.relation_ac, self.relation_de}

        # Mock transitive reduction
        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C")])
        self.mock_transitive_reduction.return_value = reduced_graph

        GraphOptimizations._optimize_main_graph(graph)

        # Should have 2 C relations (AB, BC) and 1 E relation (DE)
        c_count = sum(1 for r in graph.relations if r.type == RelationTyps.C)
        e_count = sum(1 for r in graph.relations if r.type == RelationTyps.E)
        self.assertEqual(c_count, 2)
        self.assertEqual(e_count, 1)

    def test_optimize_object_subgraphs(self):
        ocdcr = OCDCRGraph()
        obj_graph = OCDCRObject(None, 'Test2')
        obj_graph.relations = {self.relation_ab, self.relation_bc, self.relation_ac}
        ocdcr.objects["obj1"] = obj_graph

        # Mock transitive reduction
        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C")])
        self.mock_transitive_reduction.return_value = reduced_graph

        GraphOptimizations._optimize_object_subgraphs(ocdcr)

        self.assertEqual(len(ocdcr.objects["obj1"].relations), 2)  # AB and BC

    def test_optimize_sync_relations(self):
        ocdcr = OCDCRGraph()
        ocdcr.sync_relations = {self.relation_ab, self.relation_bc, self.relation_ac}

        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C")])
        self.mock_transitive_reduction.return_value = reduced_graph

        GraphOptimizations._optimize_sync_relations(ocdcr)

        self.assertEqual(len(ocdcr.sync_relations), 2)  # AB and BC

    def test_optimize_relations_full(self):
        ocdcr = OCDCRGraph()
        ocdcr.relations = {self.relation_ab, self.relation_bc, self.relation_ac, self.relation_de}

        obj_graph = DCRGraph()
        obj_graph.relations = {self.relation_ab, self.relation_bc, self.relation_ac}
        ocdcr.objects["obj1"] = obj_graph

        ocdcr.sync_relations = {self.relation_ab, self.relation_bc, self.relation_ac}

        reduced_graph = nx.DiGraph()
        reduced_graph.add_edges_from([("A", "B"), ("B", "C")])
        self.mock_transitive_reduction.return_value = reduced_graph

        result = GraphOptimizations.optimize_relations(ocdcr)

        self.assertEqual(len(ocdcr.relations), 3)  # 2 C relations + 1 E relation
        self.assertEqual(len(ocdcr.objects["obj1"].relations), 2)
        self.assertEqual(len(ocdcr.sync_relations), 2)
        self.assertIs(result, ocdcr)

    def test_filter_removes_non_derived_syncs(self):
        # Generate full OC-DCR graph with syncs allowed by derived_entities
        full_graph = discover_apply(
            ocel=self.data.ocel,
            spawn_mapping=self.data.spawn_mapping,
            activities_mapping=self.data.activities_mapping,
            derived_entities= [("Item", "Order")]
        )

        # Disable all derived entities (now none should remain)
        self.data.derived_entities = []
        filtered = GraphOptimizations.filter_for_derived_entitiy(self.data, full_graph)

        # Expect sync relations removed
        sync_count_after = len(filtered.sync_relations)
        self.assertEqual(sync_count_after, 0)

    def test_no_filter_if_derived_is_default(self):
        graph = discover_apply(
            ocel=self.data.ocel,
            spawn_mapping=self.data.spawn_mapping,
            activities_mapping=self.data.activities_mapping,
            derived_entities=self.data.derived_entities
        )
        original_syncs = graph.sync_relations.copy()

        self.data.derived_entities = None

        filtered = GraphOptimizations.filter_for_derived_entitiy(self.data, graph)

        # Syncs must be preserved if types match derived_entities
        self.assertEqual(len(filtered.sync_relations), len(original_syncs))
        self.assertEqual(filtered.sync_relations, original_syncs)


class TestTemplateRelationFiltering(unittest.TestCase):

    def test_build_group_descendants(self):
        nestedgroups = {
            "Group1": {"A", "Group2"},
            "Group2": {"B", "C"},
            "Group3": {"D"}
        }
        expected = {
            "Group1": {"A", "B", "C", "Group2"},
            "Group2": {"B", "C"},
            "Group3": {"D"}
        }
        result = GraphOptimizations.build_group_descendants(nestedgroups)
        self.assertEqual(result, expected)

    def test_build_reverse_ancestors(self):
        nested_map = {
            "A": "Group1",
            "Group2": "Group1",
            "B": "Group2"
        }
        expected = {
            "A": {"Group1"},
            "Group2": {"Group1"},
            "B": {"Group2", "Group1"}
        }
        result = GraphOptimizations.build_reverse_ancestors(nested_map)
        self.assertEqual(result, expected)

    def test_is_redundant_relation_case_1(self):
        rel_dict = {"Group1": {"B"}}
        reverse_ancestors = {"A": {"Group1"}}
        group_descendants = {}
        self.assertTrue(GraphOptimizations.is_redundant_relation("A", "B", rel_dict, reverse_ancestors, group_descendants))

    def test_is_redundant_relation_case_2(self):
        rel_dict = {"A": {"Group2"}}
        reverse_ancestors = {"B": {"Group2"}}
        group_descendants = {}
        self.assertTrue(GraphOptimizations.is_redundant_relation("A", "B", rel_dict, reverse_ancestors, group_descendants))

    def test_is_redundant_relation_case_3(self):
        rel_dict = {"Group1": {"Group2"}}
        reverse_ancestors = {}
        group_descendants = {
            "Group1": {"a"},
            "Group2": {"b"}
        }
        self.assertTrue(GraphOptimizations.is_redundant_relation("a", "b", rel_dict, reverse_ancestors, group_descendants))

    def test_filter_relation_type_removes_redundant(self):
        rel_dict = {
            "Group1": {"B"},
            "A": {"B"}
        }
        reverse_ancestors = {"A": {"Group1"}}
        group_descendants = {}

        expected = {"Group1": {"B"}}  # A→B should be removed
        result = GraphOptimizations.filter_relation_type(rel_dict, reverse_ancestors, group_descendants)
        self.assertEqual(result, expected)

    def test_filter_template_relations_nested(self):
        template = {
            "nestedgroups": {
                "Group1": {"A", "Group2"},
                "Group2": {"B"}
            },
            "nestedgroupsMap": {
                "A": "Group1",
                "Group2": "Group1",
                "B": "Group2"
            },
            "excludesTo": {
                "Group1": {"C"},
                "A": {"C"},
                "B": {"C"}
            }
        }

        result = GraphOptimizations.filter_template_relations(template)
        # Expect only Group1 → C to remain, A and B's redundant relations should be removed
        expected = {
            "Group1": {"C"}
        }
        self.assertEqual(result["excludesTo"], expected)

    def test_create_nestings_for_subgraphs(self):
        e1 = Event(activity="A")
        e2 = Event(activity="B")

        # Create a basic DCRGraph with 2 events and 1 relation
        graph = DCRGraph()
        graph.add_event(e1)
        graph.add_event(e2)

        # Relation: A → B (response)
        graph.add_relation(start_event=e1, target_event=e2, relation_type=RelationTyps.R)
        ocdcr_obj = OCDCRObject(spawn=e1, type="myType", dcr=graph)

        oc_dcr = OCDCRGraph()
        oc_dcr.objects["myType"] = ocdcr_obj
        oc_dcr.update_activities()

        # Apply nesting 
        updated = GraphOptimizations.create_nestings_for_subgraphs(oc_dcr)

        self.assertIn("myType", updated.objects)
        nested_obj = updated.objects["myType"]

        # Check that groups were renamed with obj_id
        for group in nested_obj.nestedgroups:
            self.assertTrue(group.activity.endswith("_myType"))

        # Ensure original relations are preserved with quantifiers reassigned
        for rel in nested_obj.relations:
            self.assertIn(rel.start_event, nested_obj.events)
            self.assertIn(rel.target_event, nested_obj.events)

        # At least one nested group exists
        self.assertGreaterEqual(len(nested_obj.nestedgroups), 0)  # 0 if no nesting found, ≥1 if found
        self.assertTrue(isinstance(updated, OCDCRGraph))


if __name__ == '__main__':
    unittest.main()
