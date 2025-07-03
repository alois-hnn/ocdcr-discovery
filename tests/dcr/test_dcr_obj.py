
import unittest
from ocpa.objects.oc_dcr_graph import RelationTyps, Event, OCDCRGraph, OCDCRObject, DCRGraph, MarkingTyps,DCRMarking,DCRRelation,OCDCRRelation, IN_TOP_GRAPH
import copy

class TestDCRMarking(unittest.TestCase):
    def setUp(self):
        self.marking = DCRMarking()
        self.event1 = Event("Activity1")
        self.event2 = Event("Activity2")
        self.event3 = Event("Activity3")

    def test_add_event(self):
        self.marking.add_event(self.event1, MarkingTyps.E)
        self.assertIn(self.event1, self.marking.executed)
        
        self.marking.add_event(self.event2, MarkingTyps.P)
        self.assertIn(self.event2, self.marking.pending)
        
        self.marking.add_event(self.event1, MarkingTyps.I)
        self.assertIn(self.event1, self.marking.included)

    def test_get_set(self):
        self.marking.add_event(self.event1, MarkingTyps.E)
        self.assertEqual(self.marking.get_set(MarkingTyps.E), {self.event1})
        
        self.marking.add_event(self.event2, MarkingTyps.P)
        self.assertEqual(self.marking.get_set(MarkingTyps.P), {self.event2})

        self.marking.add_event(self.event2, MarkingTyps.I)
        self.assertEqual(self.marking.get_set(MarkingTyps.I), {self.event2})

    def test_get_event_marking(self):
        # Test single markings
        self.marking.add_event(self.event1, MarkingTyps.E)
        self.assertEqual(self.marking.get_event_marking(self.event1), {MarkingTyps.E})
        
        self.marking.add_event(self.event2, MarkingTyps.P)
        self.assertEqual(self.marking.get_event_marking(self.event2), {MarkingTyps.P})
        
        # Test multiple markings
        self.marking.add_event(self.event3, MarkingTyps.I)
        self.marking.add_event(self.event3, MarkingTyps.P)
        self.assertEqual(self.marking.get_event_marking(self.event3), 
                        {MarkingTyps.I, MarkingTyps.P})
        
        # Test non-existent event (should return empty set, not None)
        self.assertEqual(self.marking.get_event_marking(Event("NonExistent")), set())
        
        # Test clearing markings
        self.marking.executed.remove(self.event1)
        self.assertEqual(self.marking.get_event_marking(self.event1), set())
    def test_remove_event_from_all_markings(self):
        """Test removing an event marked as E, P, and I"""
        m = DCRMarking()
        e = Event("TestEvent")

        # Add event to all markings
        m.add_event(e, MarkingTyps.E)
        m.add_event(e, MarkingTyps.P)
        m.add_event(e, MarkingTyps.I)

        # Confirm it's in all sets
        self.assertIn(e, m.executed)
        self.assertIn(e, m.pending)
        self.assertIn(e, m.included)

        # Remove event
        m.remove_event(e)

        # Confirm it's gone from all sets
        self.assertNotIn(e, m.executed)
        self.assertNotIn(e, m.pending)
        self.assertNotIn(e, m.included)
        self.assertEqual(m.get_event_marking(e), set())

    def test_remove_event_only_in_one_marking(self):
        """Test removing an event from a single marking"""
        m = DCRMarking()
        e = Event("OnlyIncluded")
        m.add_event(e, MarkingTyps.I)

        m.remove_event(e)

        self.assertNotIn(e, m.included)
        self.assertEqual(m.get_event_marking(e), set())

    def test_remove_event_not_present(self):
        """Test removing an event that was never marked"""
        m = DCRMarking()
        e = Event("NotPresent")

        # Should not raise
        m.remove_event(e)

        # Still empty
        self.assertEqual(len(m.executed), 0)
        self.assertEqual(len(m.pending), 0)
        self.assertEqual(len(m.included), 0)

class TestEvent(unittest.TestCase):
    def test_event_creation(self):
        event = Event("TestActivity")
        self.assertEqual(event.activity, "TestActivity")
        self.assertFalse(event.isGroup)
        self.assertIsNone(event.parent)
        
    def test_nested_event(self):
        parent = Event("Parent", isGroup=True)
        child = Event("Child", parent=parent)
        self.assertTrue(parent.isGroup)
        self.assertEqual(child.parent, parent)

class TestDCRRelation(unittest.TestCase):
    def setUp(self):
        self.event1 = Event("Activity1")
        self.event2 = Event("Activity2")
        
    def test_relation_creation(self):
        relation = DCRRelation(self.event1, self.event2, RelationTyps.R)
        self.assertEqual(relation.start_event, self.event1)
        self.assertEqual(relation.target_event, self.event2)
        self.assertEqual(relation.type, RelationTyps.R)

class TestDCRGraph(unittest.TestCase):
    def setUp(self):
        self.graph = DCRGraph()
        self.activity1 = "Activity1"
        self.activity2 = "Activity2"
        
        self.event1 = Event(self.activity1)
        self.event2 = Event(self.activity2)
        self.group_event = Event("Group", isGroup=True)
        self.nested_event = Event("Nested", parent=self.group_event)
        
        self.relation = DCRRelation(self.event1, self.event2, RelationTyps.R)
        
        self.marking = DCRMarking()
        self.marking.add_event(self.event1, MarkingTyps.E)
        self.marking.add_event(self.event2, MarkingTyps.I)
        
        self.nested_groups = {self.group_event: {self.nested_event}}
        self.nested_events = {self.nested_event}

    def test_from_attributes_creates_graph(self):
        """Test that from_attributes creates a valid DCRGraph instance"""
        graph = DCRGraph.from_attributes(
            events={self.event1},
            relations=set(),
            marking=DCRMarking(),
            nested_groups={},
            nested_events=set()
        )
        self.assertIsInstance(graph, DCRGraph)
        self.assertEqual(len(graph.events), 1)

    def test_from_attributes_with_relations(self):
        """Test that relations are properly copied"""
        graph = DCRGraph.from_attributes(
            events={self.event1, self.event2},
            relations={self.relation},
            marking=DCRMarking(),
            nested_groups={},
            nested_events=set()
        )
        self.assertEqual(len(graph.relations), 1)
        relation = next(iter(graph.relations))
        self.assertEqual(relation.type, RelationTyps.R)

    def test_from_attributes_with_nested_groups(self):
        """Test that nested group structure is maintained"""
        graph = DCRGraph.from_attributes(
            events={self.group_event, self.nested_event},
            relations=set(),
            marking=DCRMarking(),
            nested_groups=self.nested_groups,
            nested_events=self.nested_events
        )
        
        # Verify the group structure
        self.assertEqual(len(graph.nestedgroups), 1)
        parent = next(iter(graph.nestedgroups.keys()))
        child = next(iter(graph.nestedgroups[parent]))
        self.assertEqual(child.parent, parent)

    def test_from_attributes_with_marking(self):
        """Test that marking is properly copied"""
        graph = DCRGraph.from_attributes(
            events={self.event1},
            relations=set(),
            marking=self.marking,
            nested_groups={},
            nested_events=set()
        )
        self.assertEqual(len(graph.marking.executed), 1)
        self.assertEqual(len(graph.marking.included), 1)  
        
    def test_add_event(self):
        self.graph.add_event(self.activity1)
        self.assertEqual(len(self.graph.events), 1)
        event = next(iter(self.graph.events))
        self.assertEqual(event.activity, self.activity1)
        self.assertIn(event, self.graph.marking.included)
        self.assertFalse(event.isGroup)
        self.assertIsNone(event.parent)

    def test_add_event_group(self):
         # Test group event creation
        self.graph.add_event("Group1", isGroup=True)
        group = self.graph.get_event("Group1")
        self.assertTrue(group.isGroup)
        self.assertIn(group, self.graph.nestedgroups)
        self.assertEqual(len(self.graph.nestedgroups[group]), 0)

        # Test event with parent (string)
        self.graph.add_event("Child1", parent="Group1")
        child = self.graph.get_event("Child1")
        self.assertEqual(child.parent, group)
        self.assertIn(child, self.graph.nestedgroups[group])
        self.assertTrue(group.isGroup)  

    def test_add_event_group_no_parent(self):
        # Test automatic parent creation when missing
        self.graph.add_event("Child2", parent="NonExistentParent")
        parent = self.graph.get_event("NonExistentParent")
        self.assertTrue(parent.isGroup)
        child = self.graph.get_event("Child2")
        self.assertEqual(child.parent, parent)
        self.assertIn(child, self.graph.nestedgroups[parent])

    def test_add_event_marking(self):
        # Test marking types
        self.graph.add_event("PendingActivity", {MarkingTyps.P})
        pending = self.graph.get_event("PendingActivity")
        self.assertIn(pending, self.graph.marking.pending)

        self.graph.add_event("ExecutedActivity", {MarkingTyps.E})
        executed = self.graph.get_event("ExecutedActivity")
        self.assertIn(executed, self.graph.marking.executed)

    def test_add_event_nested_complex(self):
        # Test complex nested structure
        self.graph.add_event("TopGroup", isGroup=True)
        self.graph.add_event("MidGroup", parent="TopGroup", isGroup=True)
        self.graph.add_event("Leaf", parent="MidGroup")

        top = self.graph.get_event("TopGroup")
        mid = self.graph.get_event("MidGroup")
        leaf = self.graph.get_event("Leaf")

        self.assertTrue(top.isGroup)
        self.assertTrue(mid.isGroup)
        self.assertFalse(leaf.isGroup)
        self.assertEqual(mid.parent, top)
        self.assertEqual(leaf.parent, mid)
        self.assertIn(mid, self.graph.nestedgroups[top])
        self.assertIn(leaf, self.graph.nestedgroups[mid])

    def test_add_event_event_to_parent(self):
        # Test parent is converted to group when adding children
        self.graph.add_event("RegularEvent")
        self.graph.add_event("NewChild", parent="RegularEvent")
        regular = self.graph.get_event("RegularEvent")
        self.assertTrue(regular.isGroup)  
        self.assertIn(self.graph.get_event("NewChild"), self.graph.nestedgroups[regular])
        
    def test_add_relation(self):
        # Test basic relation addition
        self.graph.add_event(self.activity1)
        self.graph.add_event(self.activity2)
        self.graph.add_relation(self.activity1, self.activity2, RelationTyps.R)
        self.assertEqual(len(self.graph.relations), 1)
        relation = next(iter(self.graph.relations))
        self.assertEqual(relation.start_event.activity, self.activity1)
        self.assertEqual(relation.target_event.activity, self.activity2)
        self.assertEqual(relation.type, RelationTyps.R)

        # Test adding relation with Event objects directly
        event3 = self.graph.add_event("Activity3")
        event4 = self.graph.add_event("Activity4")
        self.graph.add_relation(event3, event4, RelationTyps.C)
        self.assertEqual(len(self.graph.relations), 2)
        
        # Test adding duplicate relation (should not create new relation)
        initial_count = len(self.graph.relations)
        self.graph.add_relation(self.activity1, self.activity2, RelationTyps.R)
        self.assertEqual(len(self.graph.relations), initial_count)

        # Test adding different relation types between same events
        self.graph.add_relation(self.activity1, self.activity2, RelationTyps.I)
        self.assertEqual(len(self.graph.relations), 3)  # Should allow multiple relation types between same events

        # Test adding relation with non-existent events
        with self.assertRaises(ValueError):
            self.graph.add_relation("NonExistent1", self.activity2, RelationTyps.R)
        
        with self.assertRaises(ValueError):
            self.graph.add_relation(self.activity1, "NonExistent2", RelationTyps.R)

        # Test mixing string and Event objects (should raise TypeError)
        event5 = self.graph.add_event("Activity5")
        with self.assertRaises(TypeError):
            self.graph.add_relation("Activity1", event5, RelationTyps.R)
        
        with self.assertRaises(TypeError):
            self.graph.add_relation(event5, "Activity2", RelationTyps.R)

        # Test adding all relation types
        relation_types = [RelationTyps.R, RelationTyps.C, RelationTyps.I, RelationTyps.E]
        for rel_type in relation_types:
            self.graph.add_event(f"Start{rel_type.name}")
            self.graph.add_event(f"Target{rel_type.name}")
            self.graph.add_relation(f"Start{rel_type.name}", f"Target{rel_type.name}", rel_type)
        
        # Verify all relation types were added correctly
        self.assertEqual(len(self.graph.relations), 3 + len(relation_types))  # Initial 3 + new relations
        for rel_type in relation_types:
            rel = self.graph.get_relation(
                self.graph.get_event(f"Start{rel_type.name}"),
                self.graph.get_event(f"Target{rel_type.name}"),
                rel_type
            )
            self.assertIsNotNone(rel)
            self.assertEqual(rel.type, rel_type)

        # Test relation between nested events
        self.graph.add_event("ParentGroup", isGroup=True)
        self.graph.add_event("ChildEvent", parent="ParentGroup")
        self.graph.add_relation("ChildEvent", self.activity1, RelationTyps.E)
        child_event = self.graph.get_event("ChildEvent")
        rel = self.graph.get_relation(child_event, self.graph.get_event(self.activity1), RelationTyps.E)
        self.assertIsNotNone(rel)
        self.assertEqual(rel.type, RelationTyps.E)

    def test_get_relation(self):
        # Setup test events
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        event3 = self.graph.add_event("Activity3")
        
        # Add different types of relations
        include_rel = DCRRelation(event1, event2, RelationTyps.I)
        response_rel = DCRRelation(event2, event1, RelationTyps.R)
        condition_rel = DCRRelation(event3, event1, RelationTyps.C)
        
        self.graph.add_relation(event1, event2, RelationTyps.I)
        self.graph.add_relation(event2, event1, RelationTyps.R)
        self.graph.add_relation(event3, event1, RelationTyps.C)

        # Test retrieving each relation
        self.assertEqual(
            self.graph.get_relation(event1, event2, RelationTyps.I),
            include_rel
        )

        # Test non-existent relations
        self.assertIsNone(
            self.graph.get_relation(event1, event3, RelationTyps.R)
        )

        # Test with same relation type but different direction
        self.assertIsNone(
            self.graph.get_relation(event1, event2, RelationTyps.R)
        )  # Exists in opposite direction only

        # Test with nested events
        self.graph.add_event("GroupEvent", isGroup=True)
        nested_event = self.graph.add_event("NestedEvent", parent="GroupEvent")
        nested_rel = DCRRelation(event1, nested_event, RelationTyps.E)
        self.graph.add_relation(event1, nested_event, RelationTyps.E)
        
        self.assertEqual(
            self.graph.get_relation(event1, nested_event, RelationTyps.E),
            nested_rel
        )

        # Test with non-existent events
        non_existent = Event("NonExistent")
        self.assertIsNone(
            self.graph.get_relation(non_existent, event1, RelationTyps.R)
        )

        # Test case sensitivity in event names
        case_sensitive_event = self.graph.add_event("activity1")  # Different case
        self.assertIsNone(
            self.graph.get_relation(case_sensitive_event, event2, RelationTyps.I)
        )

    def test_remove_relation(self):
        # Setup test events and relations
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        event3 = self.graph.add_event("Activity3")
        
        # Add different types of relations
        include_rel = DCRRelation(event1, event2, RelationTyps.I)
        response_rel = DCRRelation(event2, event1, RelationTyps.R)
        
        self.graph.add_relation(event1, event2, RelationTyps.I)
        self.graph.add_relation(event2, event1, RelationTyps.R)
        self.graph.add_relation(event3, event1, RelationTyps.C)

        # Verify initial state
        self.assertEqual(len(self.graph.relations), 3)

        # Test removing existing relation
        result = self.graph.remove_relation(include_rel)
        self.assertTrue(result)
        self.assertEqual(len(self.graph.relations), 2)
        self.assertNotIn(include_rel, self.graph.relations)

        # Test removing same relation again 
        result = self.graph.remove_relation(include_rel)
        self.assertFalse(result)
        self.assertEqual(len(self.graph.relations), 2)

        # Test removing another relation type
        result = self.graph.remove_relation(response_rel)
        self.assertTrue(result)
        self.assertEqual(len(self.graph.relations), 1)
        self.assertNotIn(response_rel, self.graph.relations)

        # Test removing non-existent relation
        non_existent_rel = DCRRelation(event1, event3, RelationTyps.E)
        result = self.graph.remove_relation(non_existent_rel)
        self.assertFalse(result)
        self.assertEqual(len(self.graph.relations), 1)

        # Test with nested events
        self.graph.add_event("GroupEvent", isGroup=True)
        nested_event = self.graph.add_event("NestedEvent", parent="GroupEvent")
        nested_rel = DCRRelation(event1, nested_event, RelationTyps.E)
        self.graph.add_relation(event1, nested_event, RelationTyps.E)
        
        result = self.graph.remove_relation(nested_rel)
        self.assertTrue(result)
        self.assertEqual(len(self.graph.relations), 1)

        # Test with duplicate relations 
        dup_rel1 = DCRRelation(event1, event2, RelationTyps.I)
        dup_rel2 = DCRRelation(event1, event2, RelationTyps.I)
        self.graph.relations.add(dup_rel1)
        self.graph.relations.add(dup_rel2)
        
        # Should remove all matching relations
        result = self.graph.remove_relation(dup_rel1)
        self.assertTrue(result)
        self.assertEqual(len(self.graph.relations), 1)

        
    def test_get_event(self):
        self.graph.add_event(self.activity1)
        event = self.graph.get_event(self.activity1)
        self.assertEqual(event.activity, self.activity1)
        
    def test_add_nested_group_strings(self):
        self.graph.add_event("Parent")
        self.graph.add_event("Child1")
        self.graph.add_event("Child2")
        
        # Test adding with strings
        self.graph.add_nested_group("Parent", {"Child1", "Child2"})
        
        parent = self.graph.get_event("Parent")
        self.assertTrue(parent.isGroup)
        
        child1 = self.graph.get_event("Child1")
        child2 = self.graph.get_event("Child2")
        self.assertEqual(child1.parent, parent)
        self.assertEqual(child2.parent, parent)
        
        self.assertIn(parent, self.graph.nestedgroups)
        self.assertEqual(len(self.graph.nestedgroups[parent]), 2)
        self.assertIn(child1, self.graph.nestedgroups[parent])
        self.assertIn(child2, self.graph.nestedgroups[parent])
        
    def test_add_nested_group_events(self): 
        parent2 = Event("Parent2")
        child3 = Event("Child3")
        
        self.graph.add_nested_group(parent2, {child3})
        self.assertTrue(parent2.isGroup)
        self.assertEqual(child3.parent, parent2)
        self.assertIn(parent2, self.graph.nestedgroups)
        self.assertIn(child3, self.graph.nestedgroups[parent2])
    
    def test_add_nested_group_typeError(self): 
        # invalid parent type
        with self.assertRaises(TypeError):
            self.graph.add_nested_group(123, {"Child1"})
        
        # invalid child type
        with self.assertRaises(TypeError):
            self.graph.add_nested_group("Parent", {123})

    def test_get_incidental_relations(self):
        # Setup 
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        event3 = self.graph.add_event("Activity3")
        
        # Add different types of relations
        include_rel = DCRRelation(event1, event2, RelationTyps.I)
        response_rel = DCRRelation(event2, event1, RelationTyps.R)
        condition_rel = DCRRelation(event3, event1, RelationTyps.C)
        
        self.graph.add_relation(event1, event2, RelationTyps.I)
        self.graph.add_relation(event2, event1, RelationTyps.R)
        self.graph.add_relation(event3, event1, RelationTyps.C)

        # Test relations for event1 (both incoming and outgoing)
        event1_rels = self.graph.get_incidental_relations(event1)
        self.assertEqual(len(event1_rels), 3)
        self.assertIn(include_rel, event1_rels)
        self.assertIn(response_rel, event1_rels)
        self.assertIn(condition_rel, event1_rels)

        # Test relations for event2 (only outgoing to event1)
        event2_rels = self.graph.get_incidental_relations(event2)
        self.assertEqual(len(event2_rels), 2)
        self.assertIn(include_rel, event2_rels)
        self.assertIn(response_rel, event2_rels)

        # Test relations for event3 (only outgoing to event1)
        event3_rels = self.graph.get_incidental_relations(event3)
        self.assertEqual(len(event3_rels), 1)
        self.assertIn(condition_rel, event3_rels)

        # Test non-existent event
        non_existent = Event("NonExistent")
        self.assertEqual(len(self.graph.get_incidental_relations(non_existent)), 0)

        # Test with nested events
        self.graph.add_event("GroupEvent", isGroup=True)
        nested_event = self.graph.add_event("NestedEvent", parent="GroupEvent")
        nested_rel = DCRRelation(event1, nested_event, RelationTyps.E)
        self.graph.add_relation(event1, nested_event, RelationTyps.E)
        
        nested_rels = self.graph.get_incidental_relations(nested_event)
        self.assertEqual(len(nested_rels), 1)
        self.assertIn(nested_rel, nested_rels)

        # Test with event that has no relations
        isolated_event = self.graph.add_event("Isolated")
        self.assertEqual(len(self.graph.get_incidental_relations(isolated_event)), 0)

    def test_remove_event_basic(self):
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        
        # Add relations
        self.graph.add_relation(event1, event2, RelationTyps.I)
        self.graph.add_relation(event2, event1, RelationTyps.R)
        
        # Verify initial state
        self.assertEqual(len(self.graph.events), 2)
        self.assertEqual(len(self.graph.relations), 2)
    
        self.graph.remove_event(event1)
        
        # Verify removal
        self.assertEqual(len(self.graph.events), 1)
        self.assertEqual(len(self.graph.relations), 0)
        self.assertNotIn(event1, self.graph.events)
        self.assertIn(event2, self.graph.events)

    def test_remove_event_with_multiple_relations(self):
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        event3 = self.graph.add_event("Activity3")
        
        # Create multiple relations to event1
        self.graph.add_relation(event1, event2, RelationTyps.I)
        self.graph.add_relation(event2, event1, RelationTyps.R)
        self.graph.add_relation(event3, event1, RelationTyps.C)
        self.graph.add_relation(event1, event3, RelationTyps.E)
        self.graph.add_relation(event2, event3, RelationTyps.E)
        
        # Verify initial state
        self.assertEqual(len(self.graph.events), 3)
        self.assertEqual(len(self.graph.relations), 5)
        
        self.graph.remove_event(event1)
        
        # Verify removal
        self.assertEqual(len(self.graph.events), 2)
        self.assertEqual(len(self.graph.relations), 1)  # Only event2-event3 relation remains
        
        # Verify correct relations were removed
        remaining_relations = list(self.graph.relations)
        self.assertEqual(len(remaining_relations), 1)
        self.assertNotIn(event1, [remaining_relations[0].start_event, remaining_relations[0].target_event])

    def test_remove_nested_event(self):
        #Test removal of an event that belongs to a nested group
        # Setup
        group = self.graph.add_event("GroupEvent", isGroup=True)
        nested = self.graph.add_event("NestedEvent", parent="GroupEvent")
        
        event1 = self.graph.add_event(self.activity1)
        self.graph.add_relation(event1, nested, RelationTyps.I)
        self.graph.add_relation(nested, event1, RelationTyps.R)
        
        # Verify initial state
        self.assertEqual(len(self.graph.events), 3)
        self.assertEqual(len(self.graph.relations), 2)
        self.assertEqual(len(self.graph.nestedgroups[group]), 1)
        
        self.graph.remove_event(nested)
        
        # Verify removal
        self.assertEqual(len(self.graph.events), 2)
        self.assertEqual(len(self.graph.relations), 0)
        self.assertEqual(len(self.graph.nestedgroups[group]), 0)
        self.assertNotIn(nested, self.graph.events)

    def test_remove_nonexistent_event(self):
        #Test attempting to remove an event not in the graph
        event1 = self.graph.add_event(self.activity1)
        non_existent = Event("NonExistent")
        
        # Verify initial state
        self.assertEqual(len(self.graph.events), 1)
        
        # Attempt removal - should raise KeyError
        with self.assertRaises(KeyError):
            self.graph.remove_event(non_existent)
        
        # Verify original event remains
        self.assertEqual(len(self.graph.events), 1)
        self.assertIn(event1, self.graph.events)

    def test_remove_incidental_relations(self):
        # Setup test events and relations
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        event3 = self.graph.add_event("Activity3")
        
        # Create multiple relations
        self.graph.add_relation(event1, event2, RelationTyps.I)
        self.graph.add_relation(event2, event1, RelationTyps.R)
        self.graph.add_relation(event3, event1, RelationTyps.C)
        
        # Verify initial state
        self.assertEqual(len(self.graph.relations), 3)
        self.assertEqual(len(self.graph.get_incidental_relations(event1)), 3)
        
        # Remove relations for event1
        self.graph._remove_incidental_relations(event1)
        
        # Verify all event1's relations were removed
        self.assertEqual(len(self.graph.relations), 0)
        self.assertEqual(len(self.graph.get_incidental_relations(event1)), 0)
        
        # Relations for other events should remain unchanged
        self.assertEqual(len(self.graph.get_incidental_relations(event2)), 0)
        self.assertEqual(len(self.graph.get_incidental_relations(event3)), 0)


    def test_str_representation(self):
        self.graph.add_event(self.activity1)
        self.graph.add_event(self.activity2)
        self.graph.add_relation(self.activity1, self.activity2, RelationTyps.R)
        
        graph_str = str(self.graph)
        self.assertIsInstance(graph_str, str)
        self.assertIn(self.activity1, graph_str)
        self.assertIn(self.activity2, graph_str)
        self.assertIn("includesTo", graph_str)

    def test_initialization_from_template(self):
        dcr_template = {
            'events': {'a','b','c'},
            'marking': {'executed': 'a', 'pending': 'b',
                        'included': 'c'},
            'includesTo': {'a': {'b'}},
            'excludesTo': {'c': {'b'}},
            'responseTo': {'c': {'b'}},
            'conditionsFor': {'b': {'a'}},
            'nestedgroups': {},
            'labelMapping':{}
        }

        graph = DCRGraph(template=dcr_template)
        
        self.assertEqual(len(graph.events), 3)
        self.assertEqual(len(graph.relations), 4)
        self.assertIsNotNone(graph.get_event("a"))
        self.assertIsNotNone(graph.get_event("b"))

class TestOCDCRObject(unittest.TestCase):
    def setUp(self):
        self.spawn_event = Event("SpawnActivity")
        self.obj = OCDCRObject(self.spawn_event, "obj1")
        
    def test_initialization(self):
        self.assertEqual(self.obj.spawn, self.spawn_event)
        self.assertEqual(self.obj.type, "obj1")
        self.assertIsInstance(self.obj, DCRGraph) 

    def test_initialization_from_dcr_graph(self):
        dcr = DCRGraph()
        dcr.add_event("A")
        dcr.add_event("B")
        dcr.add_relation("A", "B", RelationTyps.R)
        
        obj = OCDCRObject(self.spawn_event, "obj2", dcr=dcr)
        
        self.assertEqual(len(obj.events), 2)
        self.assertEqual(len(obj.relations), 1)
        self.assertEqual(obj.type, "obj2")
        self.assertEqual(obj.spawn, self.spawn_event)

    def test_empty_object_conversion(self):
        """Test conversion of empty OCDCR object"""
        dcr_graph = self.obj.to_dcr()
        
        # Should contain just the spawn event
        self.assertEqual(len(dcr_graph.events), 0)
        
        # No relations or markings
        self.assertEqual(len(dcr_graph.relations), 0)
        self.assertEqual(len(dcr_graph.marking.executed), 0)
        self.assertEqual(len(dcr_graph.marking.included), 0)
        self.assertEqual(len(dcr_graph.nestedgroups), 0)

    def test_basic_conversion_with_events(self):
        """Test conversion with added events"""
        # Add some events
        event1 = self.obj.add_event("Activity1")
        event2 = self.obj.add_event("Activity2")
        
        # Convert to DCR
        dcr_graph = self.obj.to_dcr()
        
        # Verify all events are present
        self.assertEqual(len(dcr_graph.events), 2)
        self.assertIn(event1, dcr_graph.events)
        self.assertIn(event2, dcr_graph.events)

    def test_remove_event_in_object(self):
        """Test removing an event from OCDCRGraph where the event belongs to an object"""
        spawn = Event("Spawn")
        obj = OCDCRObject(spawn, "type1")
        event1 = obj.add_event("E1")
        event2 = obj.add_event("E2")
        obj.add_relation(event1, event2, RelationTyps.R)

        oc = OCDCRGraph()
        oc.add_object(obj)

        self.assertEqual(len(obj.relations), 1)
        self.assertIn(event1, obj.events)
        self.assertIn(event2, obj.events)

        oc.remove_event(event1)

        # event1 should be removed from object
        self.assertNotIn(event1, obj.events)
        # relation should be removed
        self.assertEqual(len(obj.relations), 0)
        # event2 should still exist
        self.assertIn(event2, obj.events)

    def test_remove_spawn_event_raises(self):
        """Test removing the spawn event raises ValueError"""
        oc = OCDCRGraph()
        spawn = Event("Spawn")
        obj = OCDCRObject(spawn, "type1")
        oc.add_object(obj)
        with self.assertRaises(ValueError):
            oc.remove_event(spawn)

    def test_remove_event_in_top_graph(self):
        """Test removing an event from the top-level graph (IN_TOP_GRAPH)"""
        g = OCDCRGraph()
        e = g.add_event("TopLevelEvent")

        g.remove_event(e)

        # Event should be gone
        self.assertNotIn(e, g.events)
        self.assertNotIn(e, g.activityToObject)

    def test_remove_nonexistent_event_raises(self):
        """Test removing event not in the OCDCRGraph raises KeyError"""
        oc = OCDCRGraph()
        spawn = Event("Spawn")
        obj = OCDCRObject(spawn, "type1")
        oc.add_object(obj)
        fake_event = Event("NotInGraph")
        with self.assertRaises(KeyError):
            oc.remove_event(fake_event)

    def test_relation_conversion(self):
        """Test that relations are converted without quantifiers"""
        # Add events and relations
        event1 = self.obj.add_event("Activity1")
        event2 = self.obj.add_event("Activity2")
        self.obj.add_relation(event1, event2, RelationTyps.R, 
                            quantifier_head=True, quantifier_tail=False)
        
        # Convert to DCR
        dcr_graph = self.obj.to_dcr()
        
        # Verify relation was converted
        self.assertEqual(len(dcr_graph.relations), 1)
        relation = next(iter(dcr_graph.relations))
        
        # Should be basic DCRRelation without quantifiers
        self.assertIsInstance(relation, DCRRelation)
        self.assertEqual(relation.type, RelationTyps.R)
        
        # Verify the relation connects the right events
        self.assertEqual(relation.start_event.activity, "Activity1")
        self.assertEqual(relation.target_event.activity, "Activity2")

    def test_marking_conversion(self):
        """Test that markings are preserved"""
        event1 = self.obj.add_event("Activity1")
        self.obj.marking.add_event(event1, MarkingTyps.E)
        self.obj.marking.add_event(self.spawn_event, MarkingTyps.I)
        
        dcr_graph = self.obj.to_dcr()
        
        # Verify markings
        self.assertEqual(len(dcr_graph.marking.executed), 1)
        self.assertEqual(len(dcr_graph.marking.included), 2) #event1 + spawn
        
        # Find the events to check their markings
        for event in dcr_graph.events:
            if event.activity == "Activity1":
                self.assertIn(MarkingTyps.E, dcr_graph.marking.get_event_marking(event))
            elif event.activity == "SpawnActivity":
                self.assertIn(MarkingTyps.I, dcr_graph.marking.get_event_marking(event))

    def test_nested_group_conversion(self):
        """Test that nested groups are preserved"""
        # Create group structure
        group = self.obj.add_event("Group", isGroup=True)
        nested = self.obj.add_event("Nested", parent="Group")
        
        dcr_graph = self.obj.to_dcr()
        
        # Verify group structure
        self.assertEqual(len(dcr_graph.nestedgroups), 1)
        copied_group = next(iter(dcr_graph.nestedgroups.keys()))
        copied_nested = next(iter(dcr_graph.nestedgroups[copied_group]))
        
        self.assertEqual(copied_group.activity, "Group")
        self.assertEqual(copied_nested.activity, "Nested")
        self.assertEqual(copied_nested.parent, copied_group)
        
    def test_object_id_setter(self):
        self.obj.type = "new_id"
        self.assertEqual(self.obj.type, "new_id")
        
    def test_add_event(self):
        """Test that inherited method add_event works"""
        self.obj.add_event("Activity1")
        event = self.obj.get_event("Activity1")
        self.assertEqual(event.activity, "Activity1")
        self.assertIn(event, self.obj.marking.included)
        
    def test_add_relation_with_strings(self):
        """Test adding relation with string event names"""
        self.obj.add_event("StartEvent")
        self.obj.add_event("TargetEvent")
        
        self.obj.add_relation("StartEvent", "TargetEvent", RelationTyps.R, True, False)
        
        self.assertEqual(len(self.obj.relations), 1)
        relation = next(iter(self.obj.relations))
        self.assertEqual(relation.start_event.activity, "StartEvent")
        self.assertEqual(relation.target_event.activity, "TargetEvent")
        self.assertEqual(relation.type, RelationTyps.R)
        self.assertTrue(relation.quantifier_head)
        self.assertFalse(relation.quantifier_tail)
        
    def test_add_relation_with_events(self):
        """Test adding relation with Event objects directly"""
        start = Event("StartEvent")
        target = Event("TargetEvent")
        self.obj.events.add(start)
        self.obj.events.add(target)
        
        self.obj.add_relation(start, target, RelationTyps.C, False, True)
        
        self.assertEqual(len(self.obj.relations), 1)
        relation = next(iter(self.obj.relations))
        self.assertEqual(relation.start_event, start)
        self.assertEqual(relation.target_event, target)
        self.assertEqual(relation.type, RelationTyps.C)
        self.assertFalse(relation.quantifier_head)
        self.assertTrue(relation.quantifier_tail)
        
    def test_add_relation_type_error(self):
        """Test TypeError when mixing strings and Events"""
        self.obj.add_event("StartEvent")
        target = Event("TargetEvent")
        self.obj.events.add(target)
        
        with self.assertRaises(TypeError):
            self.obj.add_relation("StartEvent", target, RelationTyps.R)
            
        with self.assertRaises(TypeError):
            self.obj.add_relation(target, "StartEvent", RelationTyps.R)
            
    def test_relation_quantifier_defaults(self):
        """Test that quantifiers default to True"""
        self.obj.add_event("StartEvent")
        self.obj.add_event("TargetEvent")
        
        self.obj.add_relation("StartEvent", "TargetEvent", RelationTyps.E)
        
        relation = next(iter(self.obj.relations))
        self.assertFalse(relation.quantifier_head)
        self.assertFalse(relation.quantifier_tail)

    def test_relation_quantifier_no_spawn(self):
        """Test that quantifiers default to True"""
        obj = OCDCRObject(None,"obj")
        obj.add_event("StartEvent")
        obj.add_event("TargetEvent")
        
        obj.add_relation("StartEvent", "TargetEvent", RelationTyps.E, True,True)
        
        relation = next(iter(obj.relations))
        self.assertFalse(relation.quantifier_head)
        self.assertFalse(relation.quantifier_tail)

    def test_add_relation_dublicated(self):
        event1 = self.obj.add_event("Activity1")
        event2 = self.obj.add_event("Activity2")
        event3 = self.obj.add_event("Activity3")

        # Test updating quantifiers on existing relation
        self.obj.add_relation(event1, event2, RelationTyps.R)
        self.obj.add_relation(event1, event2, RelationTyps.R, True, True)
        relation = self.obj.get_relation(event1, event2, RelationTyps.R)
        self.assertTrue(relation.quantifier_head)
        self.assertTrue(relation.quantifier_tail)
        self.assertEqual(len(self.obj.relations), 1)  # nothing added

        # Test adding different relation types between same events
        self.obj.add_relation(event1, event2, RelationTyps.I)
        self.assertEqual(len(self.obj.relations), 2)
        self.assertIsNotNone(self.obj.get_relation(event1, event2, RelationTyps.I))

        # Test error cases
        with self.assertRaises(ValueError):
            self.obj.add_relation("NonExistent", "Activity2", RelationTyps.R)
        
        with self.assertRaises(ValueError):
            self.obj.add_relation("Activity1", "NonExistent", RelationTyps.R)

        with self.assertRaises(TypeError):
            self.obj.add_relation("Activity1", event3, RelationTyps.R)
        
        with self.assertRaises(TypeError):
            self.obj.add_relation(event3, "Activity2", RelationTyps.R)


class TestOCDCRGraph(unittest.TestCase):
    def setUp(self):
        self.graph = OCDCRGraph()
        self.spawn_event = Event("Spawn")
        self.obj = OCDCRObject(self.spawn_event, "obj1")
        self.group_name = "GroupEvent"
        self.activity1 = "Activity1"
        self.activity2 = "Activity2"
        
    def test_add_object(self):
        self.graph.add_object(self.obj)
        self.assertIn("obj1", self.graph.objects)
        self.assertEqual(self.graph.objects["obj1"], self.obj)
        self.assertEqual(self.graph.spawn_relations[self.spawn_event], "obj1")
        
    def test_add_sync_relation(self):
        self.graph.add_event("Activity1")
        self.graph.add_event("Activity2")
        
        self.graph._add_sync_relation("Activity1", "Activity2", RelationTyps.R, quantifier_head=True, quantifier_tail=False)
        
        self.assertEqual(len(self.graph.sync_relations), 1)
        relation = next(iter(self.graph.sync_relations))
        self.assertEqual(relation.start_event.activity, "Activity1")
        self.assertEqual(relation.target_event.activity, "Activity2")
        self.assertEqual(relation.type, RelationTyps.R)
        self.assertTrue(relation.quantifier_head)
        self.assertFalse(relation.quantifier_tail)
        
    def test_get_object(self):
        self.graph.add_object(self.obj)
        obj_graph = self.graph.get_object_graph("obj1")
        self.assertEqual(obj_graph, self.obj)
        
    def test_get_events(self):
        # Test getting all events
        self.obj.add_event("Activity1")
        self.graph.add_object(self.obj)
        self.graph.add_event("GlobalActivity")
        
        events = self.graph.get_events()
        self.assertEqual(len(events), 3)  # Spawn event + Activity1 + GlobalActivity
        activities = {e.activity for e in events}
        self.assertIn("Spawn", activities)
        self.assertIn("Activity1", activities)
        self.assertIn("GlobalActivity", activities)

    def test_get_events_simple(self):
        # Test empty graph
        self.assertEqual(len(self.graph.get_events()), 0)

        # Test with only global events
        self.graph.add_event("Global1")
        self.graph.add_event("Global2")
        global_events = self.graph.get_events()
        self.assertEqual(len(global_events), 2)
        self.assertIn(self.graph.get_event("Global1"), global_events)
        self.assertIn(self.graph.get_event("Global2"), global_events)

    def test_get_events_object(self):
        # Test with only object events
        obj_graph = OCDCRGraph()
        obj = OCDCRObject(Event("SpawnObj"), "obj1")
        obj.add_event("ObjActivity1")
        obj.add_event("ObjActivity2")
        obj_graph.add_object(obj)
        obj_events = obj_graph.get_events()
        self.assertEqual(len(obj_events), 3)  # Spawn + 2 activities
        self.assertIn(obj_graph.get_event("SpawnObj"), obj_events)
        self.assertIn(obj_graph.get_event("ObjActivity1"), obj_events)
        self.assertIn(obj_graph.get_event("ObjActivity2"), obj_events)

    def test_get_events_mixed(self):
        # Test with mixed global and object events
        obj1 = OCDCRObject(Event("Spawn1"), "type1")
        obj2 = OCDCRObject(Event("Spawn2"), "type2")
        self.graph.add_object(obj1)
        self.graph.add_object(obj2)
        obj1.add_event("Obj1_Activity1")
        obj1.add_event("Obj1_Activity2")
        obj2.add_event("Obj2_Activity1")

        all_events = self.graph.get_events()
        expected_count = (
            2 +  # obj1 events
            1 +  # obj2 event
            2    # Spawn events
        )
        self.assertEqual(len(all_events), expected_count)
        
        # Test all expected events
        self.assertIn(self.graph.get_event("Obj1_Activity1"), all_events)
        self.assertIn(self.graph.get_event("Obj1_Activity2"), all_events)
        self.assertIn(self.graph.get_event("Obj2_Activity1"), all_events)
        self.assertIn(self.graph.get_event("Spawn1"), all_events)
        self.assertIn(self.graph.get_event("Spawn2"), all_events)

        # Test event uniqueness
        with self.assertRaises(ValueError):
            self.graph.add_event("Obj1_Activity1")

        # Test with nested groups
        self.graph.add_event("GroupEvent", isGroup=True)
        self.graph.add_event("NestedEvent", parent="GroupEvent")
        
        all_events = self.graph.get_events()
        
        # Convert to activity names for easier comparison
        event_activities = {e.activity for e in all_events}
        
        # Verify both events exist by activity name
        self.assertIn("GroupEvent", event_activities)
        self.assertIn("NestedEvent", event_activities)
        
        # verification of parent relationship
        nested_from_graph = self.graph.get_event("NestedEvent")
        group_from_graph = self.graph.get_event("GroupEvent")
        self.assertEqual(nested_from_graph.parent, group_from_graph)

    def test_get_event(self):
        self.graph.add_object(self.obj)
        self.obj.add_event("Obj1_Activity")
        
        self.graph.add_event("GlobalActivity")

        # Test finding global event
        global_event = self.graph.get_event("GlobalActivity")
        self.assertIsNotNone(global_event)
        self.assertEqual(global_event.activity, "GlobalActivity")
        
        # Test finding object event
        obj1_event = self.graph.get_event("Obj1_Activity")
        self.assertIsNotNone(obj1_event)
        self.assertEqual(obj1_event.activity, "Obj1_Activity")
        
        # Test finding spawn event
        spawn1 = self.graph.get_event("Spawn")
        self.assertIsNotNone(spawn1)
        self.assertEqual(spawn1.activity, "Spawn")
        
        # Test non-existent event
        non_existent = self.graph.get_event("NonExistent")
        self.assertIsNone(non_existent)

    def test_add_simple_event(self):
        """Test adding a basic event to top level"""
        event = self.graph._add_event_to_top_level(self.activity1)
        
        self.assertEqual(event.activity, self.activity1)
        self.assertFalse(event.isGroup)
        self.assertIsNone(event.parent)
        
        self.assertIn(event, self.graph.events)
        self.assertEqual(self.graph.activityToObject[event], IN_TOP_GRAPH)
        
        self.assertEqual(self.graph.marking.get_event_marking(event), {MarkingTyps.I})

    def test_add_top_level_event(self):
        """Test adding an event to the top level graph"""
        event = self.graph.add_event(self.activity1)
        
        self.assertEqual(event.activity, self.activity1)
        self.assertFalse(event.isGroup)
        self.assertIsNone(event.parent)
        
        self.assertIn(event, self.graph.events)
        self.assertEqual(self.graph.activityToObject[event], IN_TOP_GRAPH)

        self.assertEqual(self.graph.marking.get_event_marking(event), {MarkingTyps.I})

    def test_add_event_to_object(self):
        self.graph.add_object(self.obj)
        event = self.graph.add_event(self.activity1, obj="obj1")
        
        self.assertIn(event, self.obj.events)
        
        self.assertNotIn(event, self.graph.events)

        self.assertEqual(self.graph.activityToObject[event], "obj1")

    def test_add_event_with_custom_marking(self):
        """Test adding event with specific marking"""
        event = self.graph._add_event_to_top_level(
            self.activity1,
            marking={MarkingTyps.E, MarkingTyps.P}
        )
        
        self.assertEqual(
            self.graph.marking.get_event_marking(event),{MarkingTyps.E, MarkingTyps.P})

    def test_add_group_event(self):
        """Test adding a group event to top level"""
        group = self.graph._add_event_to_top_level(
            self.group_name,isGroup=True)
        
        # Verify group properties
        self.assertTrue(group.isGroup)
        self.assertIn(group, self.graph.nestedgroups)
        self.assertEqual(len(self.graph.nestedgroups[group]), 0)

    def test_add_nested_event(self):
        """Test adding nested event to top level"""
        group = self.graph._add_event_to_top_level(self.group_name,isGroup=True)
        
        # add nested event
        nested = self.graph._add_event_to_top_level("NestedEvent",parent=self.group_name)
        
        # Verify parent-child relationship
        self.assertEqual(nested.parent, group)
        self.assertIn(nested, self.graph.nestedgroups[group])
        self.assertEqual(self.graph.activityToObject[nested], IN_TOP_GRAPH)

    def test_add_existing_event(self):
        """Test adding an existing Event object"""
        existing_event = Event(self.activity1)
        event = self.graph._add_event_to_top_level(existing_event)
        
        # Should return the same event object
        self.assertIs(event, existing_event)
        self.assertIn(event, self.graph.events)

    def test_add_event_with_invalid_parent(self):
        self.graph._add_event_to_top_level( "ChildEvent", parent="NonExistentParent")
        self.assertEqual(self.graph.get_event("ChildEvent").parent, self.graph.get_event("NonExistentParent"))
        self.assertIn(self.graph.get_event("ChildEvent"), self.graph.nestedgroups[
            self.graph.get_event("NonExistentParent")])
        self.assertEqual(self.graph.activityToObject[self.graph.get_event("ChildEvent")], IN_TOP_GRAPH)

    def test_add_event_to_nonexistent_object(self):
        """Test adding event to non-existent object"""
        with self.assertRaises(KeyError):
            self.graph.add_event(self.activity1, obj="NonExistentObject")

    def test_add_existing_event_object(self):
        self.graph.add_object(self.obj)
        existing_event = Event(self.activity1)
        event = self.graph.add_event(existing_event, obj="obj1")
        
        # Should return same event object
        self.assertIs(event, existing_event)
        self.assertIn(event, self.obj.events)

    def test_default_marking(self):
        """Verify default marking is applied when none specified"""
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2, marking=set())
        
        # Default
        self.assertEqual(self.graph.marking.get_event_marking(event1), {MarkingTyps.I})
        
        # Explicit empty marking should be respected
        self.assertEqual(self.graph.marking.get_event_marking(event2), set())

    def test_activity_to_object_mapping(self):
        """Verify all added events are properly mapped"""
        event1 = self.graph._add_event_to_top_level(self.activity1)
        event2 = self.graph._add_event_to_top_level(self.activity2)
        
        self.assertEqual(self.graph.activityToObject[event1], IN_TOP_GRAPH)
        self.assertEqual(self.graph.activityToObject[event2], IN_TOP_GRAPH)
        self.assertEqual(len(self.graph.activityToObject), 2)

    def test_get_relation(self):
        # Setup
        self.graph.add_event("GlobalActivity")
        self.obj.add_event("Obj1_Activity1")
        self.obj.add_event("Obj1_Activity2")
        self.obj2 = OCDCRObject(Event("Spawn2"), "type2")
        self.obj2.add_event("Obj2_Activity1")
        self.graph.add_object(self.obj2)
        self.graph.add_object(self.obj)
        self.graph.add_relation("GlobalActivity", "Obj1_Activity1", RelationTyps.R)
        self.obj.add_relation("Obj1_Activity1", "Obj1_Activity2", RelationTyps.C)
        self.graph._add_sync_relation("Obj1_Activity1", "Obj2_Activity1", RelationTyps.E,True,True)

        # Test global relation
        global_edge = self.graph.get_relation(
            self.graph.get_event("GlobalActivity"),
            self.graph.get_event("Obj1_Activity1"),
            RelationTyps.R)
        self.assertIsNotNone(global_edge)
        
        # Test object-internal relation
        obj_edge = self.graph.get_relation(
            self.graph.get_event("Obj1_Activity1"),
            self.graph.get_event("Obj1_Activity2"),
            RelationTyps.C)
        self.assertIsNotNone(obj_edge)
        
        # Test sync relation
        sync_edge = self.graph.get_relation(
            self.graph.get_event("Obj1_Activity1"),
            self.graph.get_event("Obj2_Activity1"),
            RelationTyps.E)
        self.assertIsNotNone(sync_edge)
        
        # Test non-existent relation
        none_edge = self.graph.get_relation(
            self.graph.get_event("GlobalActivity"),
            self.graph.get_event("Obj2_Activity1"),
            RelationTyps.R)
        self.assertIsNone(none_edge)

    def test_partition_between_objects(self):
        g = OCDCRGraph()

        spawn1 = Event("Spawn1")
        spawn2 = Event("Spawn2")
        obj1 = OCDCRObject(spawn1, "obj1")
        obj2 = OCDCRObject(spawn2, "obj2")

        e1 = obj1.add_event("E1")
        e2 = obj2.add_event("E2")

        g.add_object(obj1)
        g.add_object(obj2)

        rel = DCRRelation(e1, e2, RelationTyps.R)
        g.partition({rel})

        self.assertEqual(len(g.sync_relations), 1)
        r = next(iter(g.sync_relations))
        self.assertTrue(r.quantifier_head)
        self.assertTrue(r.quantifier_tail)
        self.assertEqual(r.start_event.activity, "E1")
        self.assertEqual(r.target_event.activity, "E2")
        self.assertEqual(r.type, RelationTyps.R)

    def test_partition_skips_top_level_event(self):
        g = OCDCRGraph()

        spawn = Event("Spawn")
        obj = OCDCRObject(spawn, "obj1")
        e1 = obj.add_event("E1")

        g.add_object(obj)

        top = g.add_event("Top")

        rel1 = DCRRelation(top, e1, RelationTyps.E)
        rel2 = DCRRelation(e1, top, RelationTyps.C)

        g.partition({rel1, rel2})

        self.assertEqual(len(g.sync_relations), 0)
        self.assertEqual(len(g.relations), 0)

    def test_partition_mixed_relations(self):
        g = OCDCRGraph()

        spawn1 = Event("Spawn1")
        spawn2 = Event("Spawn2")
        obj1 = OCDCRObject(spawn1, "o1")
        obj2 = OCDCRObject(spawn2, "o2")

        e1 = obj1.add_event("E1")
        e2 = obj2.add_event("E2")

        g.add_object(obj1)
        g.add_object(obj2)

        top = g.add_event("TopEvent")
        rel1 = DCRRelation(e1, e2, RelationTyps.I)  # should be added
        rel2 = DCRRelation(e2, top, RelationTyps.C)  # should be skipped

        g.partition({rel1, rel2})

        self.assertEqual(len(g.sync_relations), 1)
        r = next(iter(g.sync_relations))
        self.assertEqual(r.type, RelationTyps.I)
        self.assertTrue(r.quantifier_head)
        self.assertTrue(r.quantifier_tail)

    def test_add_relation(self):
        self.obj.add_event("Obj1_Activity1")
        self.obj.add_event("Obj1_Activity2")
        self.obj.add_event("Obj1_Activity3")
        
        self.obj2 = OCDCRObject(Event("Spawn2"), "type2")
        self.obj2.add_event("Obj2_Activity1")
        
        self.graph.add_object(self.obj)
        self.graph.add_object(self.obj2)
        self.graph.add_event("GlobalActivity")
        self.graph.add_event("GlobalActivity2")

        # Test global to global relation
        self.graph.add_relation("GlobalActivity", "GlobalActivity2", RelationTyps.R)
        self.assertEqual(len(self.graph.relations), 1)
        
        # Test object-internal relation
        self.graph.add_relation("Obj1_Activity1", "Obj1_Activity2", RelationTyps.C)
        self.assertEqual(len(self.obj.relations), 1)
        
        # Test cross-object relation
        self.graph.add_relation("Obj1_Activity1", "Obj2_Activity1", RelationTyps.E)
        self.assertEqual(len(self.graph.sync_relations), 1)
        
        # Test global to object relation
        self.graph.add_relation("GlobalActivity", "Obj1_Activity1", RelationTyps.I)
        self.assertEqual(len(self.graph.sync_relations), 2)
        
        # Test object to global relation
        self.graph.add_relation("Obj1_Activity1", "GlobalActivity", RelationTyps.R)
        self.assertEqual(len(self.graph.sync_relations), 3)
        
        # Test quantifiers
        self.graph.add_relation("GlobalActivity2", "Obj1_Activity3", RelationTyps.C, 
                              quantifier_head=True, quantifier_tail=True)
        relation = self.graph.get_relation(self.graph.get_event("GlobalActivity2"),
                                           self.graph.get_event("Obj1_Activity3"),
                                           RelationTyps.C)
        self.assertTrue(relation.quantifier_head)
        self.assertTrue(relation.quantifier_tail)

        # Test with non-existent events
        with self.assertRaises(ValueError):
            self.graph.add_relation("NonExistent", "GlobalActivity", RelationTyps.R)
            
        with self.assertRaises(ValueError):
            self.graph.add_relation("GlobalActivity", "NonExistent", RelationTyps.R)

        # Test with mixed string/Event
        event_obj = Event("SomeEvent")
        with self.assertRaises(TypeError):
            self.graph.add_relation("GlobalActivity", event_obj, RelationTyps.R)

        # Test duplicate relation
        self.graph.add_relation("GlobalActivity", "Obj1_Activity1", RelationTyps.R)
        initial_count = len(self.graph.sync_relations)
        self.graph.add_relation("GlobalActivity", "Obj1_Activity1", RelationTyps.R)
        self.assertEqual(len(self.graph.sync_relations), initial_count)  # No duplicate added

    def test_empty_graph(self):
        """Test with empty graph"""
        relations = self.graph.get_all_relations()
        self.assertEqual(len(relations), 0)

    def test_top_level_relations(self):
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        self.graph.add_relation(self.event1, self.event2, RelationTyps.R)
        relations = self.graph.get_all_relations()
        
        self.assertEqual(len(relations), 1)
        rel = next(iter(relations))
        self.assertEqual(rel.type, RelationTyps.R)
        self.assertEqual(rel.start_event.activity, "Activity1")
        self.assertEqual(rel.target_event.activity, "Activity2")

    def test_object_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        self.obj.add_relation(self.obj_event1, self.obj_event2, RelationTyps.C)
        relations = self.graph.get_all_relations()
        
        self.assertEqual(len(relations), 1)

    def test_sync_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        self.graph._add_sync_relation(
            "Activity1", "ObjActivity1", 
            RelationTyps.I, True, False
        )
        relations = self.graph.get_all_relations()
        
        self.assertEqual(len(relations), 1)

    def test_all_relation_types(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Add one of each type
        self.graph.add_relation(self.event1, self.event2, RelationTyps.R)
        self.obj.add_relation(self.obj_event1, self.obj_event2, RelationTyps.C)
        self.graph.add_relation(
            "Activity1", "ObjActivity1", 
            RelationTyps.I, True, False
        )
        
        relations = self.graph.get_all_relations()
        self.assertEqual(len(relations), 3)
        
        # Collect all relation types
        rel_types = {rel.type for rel in relations}
        self.assertEqual(rel_types, {RelationTyps.R, RelationTyps.C, RelationTyps.I})

    def test_relation_uniqueness(self):
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Add same relation twice
        self.graph.add_relation(self.event1, self.event2, RelationTyps.R)
        self.graph.add_relation(self.event1, self.event2, RelationTyps.R)
        
        relations = self.graph.get_all_relations()
        self.assertEqual(len(relations), 1)

    def test_incidental_relations_no_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        relations = self.graph.get_incidental_relations(self.event1)
        self.assertEqual(len(relations), 0)

    def test_incidental_relations_top_level_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Add outgoing relation
        self.graph.add_relation(self.event1, self.event2, RelationTyps.R)
        # Add incoming relation
        self.graph.add_relation(self.event2, self.event1, RelationTyps.C)
        
        relations = self.graph.get_incidental_relations(self.event1)
        self.assertEqual(len(relations), 2)
        
        # Verify both relations are present
        rel_types = {rel.type for rel in relations}
        self.assertEqual(rel_types, {RelationTyps.R, RelationTyps.C})

    def test_incidental_relations_object_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Add relations within object
        self.obj.add_relation(self.obj_event1, self.obj_event2, RelationTyps.I)
        self.obj.add_relation(self.obj_event2, self.obj_event1, RelationTyps.E)
        
        relations = self.graph.get_incidental_relations(self.obj_event1)
        self.assertEqual(len(relations), 2)
        
        rel_types = {rel.type for rel in relations}
        self.assertEqual(rel_types, {RelationTyps.I, RelationTyps.E})

    def test_incidental_relations_sync_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Add sync relation from top-level to object
        self.graph._add_sync_relation(
            "Activity1", "ObjActivity1", 
            RelationTyps.R, True, False
        )
        # Add sync relation from object to top-level
        self.graph._add_sync_relation(
            "ObjActivity2", "Activity2",
            RelationTyps.C, False, True
        )
        
        # Test for top-level event
        relations = self.graph.get_incidental_relations(self.event1)
        self.assertEqual(len(relations), 1)
        self.assertEqual(next(iter(relations)).type, RelationTyps.R)
        
        # Test for object event
        relations = self.graph.get_incidental_relations(self.obj_event2)
        self.assertEqual(len(relations), 1)
        self.assertEqual(next(iter(relations)).type, RelationTyps.C)

    def test_incidental_relations_all_relation_types(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Add one of each relation type involving event1
        self.graph.add_relation(self.event1, self.event2, RelationTyps.R)  # Top-level outgoing
        self.graph.add_relation(self.event2, self.event1, RelationTyps.C)  # Top-level incoming
        self.obj.add_relation(self.obj_event1, self.event1, RelationTyps.I)  # Object to top-level
        self.graph._add_sync_relation(
            "Activity1", "ObjActivity1", 
            RelationTyps.E, True, False
        )  # Sync relation
        
        relations = self.graph.get_incidental_relations(self.event1)
        self.assertEqual(len(relations), 4)
        
        rel_types = {rel.type for rel in relations}
        self.assertEqual(rel_types, {RelationTyps.R, RelationTyps.C, RelationTyps.I, RelationTyps.E})

    def test_incidental_relations_non_existent_event(self):
        """Test that get_incidental_relations raises KeyError for non-existent event"""
        g = OCDCRGraph()
        e = Event("NonExistent")
        with self.assertRaises(KeyError):
            g.get_incidental_relations(e)

    def test_incidental_relations_nested_event_relations(self):
        self.graph.add_object(self.obj)
        self.event1 = self.graph.add_event("Activity1")
        self.event2 = self.graph.add_event("Activity2")
        self.obj_event1 = self.obj.add_event("ObjActivity1")
        self.obj_event2 = self.obj.add_event("ObjActivity2")
        # Create group structure
        group = self.graph.add_event("Group", isGroup=True)
        nested = self.graph.add_event("Nested", parent="Group")
        
        # Add relations involving nested event
        self.graph.add_relation(self.event1, nested, RelationTyps.R)
        self.graph.add_relation(nested, self.event2, RelationTyps.C)
        
        relations = self.graph.get_incidental_relations(nested)
        self.assertEqual(len(relations), 2)
        
        rel_types = {rel.type for rel in relations}
        self.assertEqual(rel_types, {RelationTyps.R, RelationTyps.C})

    def test_activity_to_object_mapping(self):
        self.obj.add_event("ObjActivity")
        self.graph.add_object(self.obj)
        
        event = self.graph.get_event("ObjActivity")
        self.assertEqual(self.graph.activityToObject[event], "obj1")

    def test_update_activities(self):
        self.graph = OCDCRGraph()
        self.spawn1 = Event("Spawn1")
        self.spawn2 = Event("Spawn2")
        self.obj1 = OCDCRObject(self.spawn1, "type1")
        self.obj2 = OCDCRObject(self.spawn2, "type2")
        self.graph.add_object(self.obj1)
        self.graph.add_object(self.obj2)
        
        # Add some test events
        self.obj1.add_event("Obj1_Activity1")
        self.obj1.add_event("Obj1_Activity2")
        self.obj2.add_event("Obj2_Activity1")
        self.top_event = self.graph.add_event("TopLevelEvent")
        
        """Test mapping updates when new events are added"""
        # Initial update
        self.graph.update_activities()
        initial_count = len(self.graph.activityToObject)
        
        # Add new events
        new_event1 = self.obj1.add_event("NewActivity1")
        new_event2 = self.graph.add_event("NewTopLevel")
        
        # Update and verify
        self.graph.update_activities()
        
        self.assertEqual(len(self.graph.activityToObject), initial_count + 2)
        self.assertEqual(self.graph.activityToObject[new_event1], "type1")
        self.assertEqual(self.graph.activityToObject.get(new_event2), IN_TOP_GRAPH)

    def test_update_activities_nested_group_events(self):
        self.graph = OCDCRGraph()
        self.spawn1 = Event("Spawn1")
        self.spawn2 = Event("Spawn2")
        self.obj1 = OCDCRObject(self.spawn1, "type1")
        self.obj2 = OCDCRObject(self.spawn2, "type2")
        self.graph.add_object(self.obj1)
        self.graph.add_object(self.obj2)
        # Create nested structure
        group = self.obj1.add_event("Group", isGroup=True)
        nested = self.obj1.add_event("Nested", parent="Group")
        
        self.graph.update_activities()
        
        # Verify both are mapped to the object
        self.assertEqual(self.graph.activityToObject[group], "type1")
        self.assertEqual(self.graph.activityToObject[nested], "type1")

    def test_remove_top_level_relation(self):
        """Test removing relation between top-level events"""
        # Add events and relation using only setup variables
        event1 = self.graph.add_event(self.activity1)
        event2 = self.graph.add_event(self.activity2)
        rel = OCDCRRelation(event1, event2, RelationTyps.R)
        self.graph.relations.add(rel)
        
        self.graph.remove_relation(rel)
        self.assertNotIn(rel, self.graph.relations)

    def test_remove_object_relation(self):
        """Test removing relation within an object"""
        # Add object and events using only setup variables
        self.graph.add_object(self.obj)
        event = self.obj.add_event(self.activity1)
        rel = OCDCRRelation(event, event, RelationTyps.C)
        self.obj.relations.add(rel)
        
        self.graph.remove_relation(rel)
        self.assertNotIn(rel, self.obj.relations)

    def test_remove_nonexistent_relation(self):
        """Test removing relation that doesn't exist"""
        # Create relation without adding it
        event = Event(self.activity1)
        rel = OCDCRRelation(event, event, RelationTyps.E)
        
        # Should not raise error
        self.graph.remove_relation(rel)

class TestCorrelation_Spawn_OCDCR(unittest.TestCase):
    def setUp(self):
        self.graph = OCDCRGraph()
        
        # Create two objects with different spawn events
        self.spawn1 = Event("Spawn1")
        self.spawn2 = Event("Spawn2")
        self.obj1 = OCDCRObject(self.spawn1, "type1")
        self.obj2 = OCDCRObject(self.spawn2, "type2")
        
        # Add objects to graph
        self.graph.add_object(self.obj1)
        self.graph.add_object(self.obj2)
        
        # Add some events
        self.obj1_event1 = self.obj1.add_event("Obj1_Activity1")
        self.obj1_event2 = self.obj1.add_event("Obj1_Activity2")
        self.obj2_event1 = self.obj2.add_event("Obj2_Activity1")
        # Add events
        self.top_event1 = self.graph.add_event("Top1")
        self.top_event2 = self.graph.add_event("Top2")
        self.obj1_event = self.obj1.add_event("Obj1Event")
        self.obj2_event = self.obj2.add_event("Obj2Event")
        
        # Add a top-level event
        self.top_event = self.graph.add_event("TopLevelEvent")

    def test_corr_with_object_event(self):
        """Test finding object for an event within an object"""
        # Event in obj1
        result = self.graph.corr(self.obj1_event1)
        self.assertIs(result, self.obj1)
        
        # Event in obj2
        result = self.graph.corr(self.obj2_event1)
        self.assertIs(result, self.obj2)

    def test_corr_with_top_level_event(self):
        """Test finding object for top-level event (should return None)"""
        result = self.graph.corr(self.top_event)
        self.assertEqual(result, IN_TOP_GRAPH)

    def test_corr_with_non_existent_event(self):
        """Test with event not in any object"""
        unknown_event = Event("NotInGraph")
        with self.assertRaises(KeyError) as context:
            self.graph.corr(unknown_event)
    def test_corr_with_duplicate_activity_names(self):
        """Test behavior when multiple objects have events with same name"""
        # Add event with same name to both objects
        self.obj1.add_event("SharedActivity")
        self.obj2.add_event("SharedActivity")
        
        # Should return the first one found (implementation dependent)
        result = self.graph.corr(Event("SharedActivity"))
        self.assertIn(result, [self.obj1, self.obj2])

    def test_spawn_with_object_event(self):
        """Test getting spawn event for an object's event"""
        result = self.graph._spawn(self.obj1_event1)
        self.assertEqual(result, self.spawn1)
        
        result = self.graph._spawn(self.obj2_event1)
        self.assertEqual(result, self.spawn2)

    def test_spawn_with_top_level_event(self):
        """Test getting spawn for top-level event (should return None)"""
        result = self.graph._spawn(self.top_event)
        self.assertIsNone(result)


    def test_nested_group_events(self):
        """Test with events in nested groups"""
        # Create nested structure in obj1
        group = self.obj1.add_event("Group", isGroup=True)
        nested = self.obj1.add_event("Nested", parent="Group")
        
        # Should still correlate to obj1
        result = self.graph.corr(nested)
        self.assertIs(result, self.obj1)
        
        # Should return obj1's spawn
        result = self.graph._spawn(nested)
        self.assertEqual(result, self.spawn1)

    def test_events_not_in_top_graph_raises(self):
        g = OCDCRGraph()
        spawn = Event("Spawn")
        obj = OCDCRObject(spawn, "Item")
        event = obj.add_event("Add Item")
        g.add_object(obj)

        with self.assertRaises(KeyError) as cm:
            g.group_top_level_events_into_unspawned_object({event}, "Item2")
        self.assertIn("not in TOP_GRAPH", str(cm.exception))

    def test_spawned_type_raises(self):
        g = OCDCRGraph()
        event = g.add_event("Accept")
        spawn = Event("Create Order")
        obj = OCDCRObject(spawn, "Order")
        g.add_object(obj)

        with self.assertRaises(KeyError) as cm:
            g.group_top_level_events_into_unspawned_object({event}, "Order")
        self.assertIn("already spawned", str(cm.exception))

    def test_successful_grouping(self):
        g = OCDCRGraph()
        e1 = g.add_event("A")
        e2 = g.add_event("B")
        g.add_relation(e1, e2, RelationTyps.C)

        g.group_top_level_events_into_unspawned_object({e1, e2}, "Unspawned")

        # Ensure new object exists
        self.assertIn("Unspawned", g.objects)

        # Ensure both events are reassigned
        obj = g.objects["Unspawned"]
        self.assertIn(e1, obj.events)
        self.assertIn(e2, obj.events)

        # Ensure original events are not in top-level
        self.assertNotIn(e1, g.events)
        self.assertNotIn(e2, g.events)

        # Ensure incidental relations are restored
        rel = OCDCRRelation(e1, e2, RelationTyps.C)
        self.assertIn(rel, obj.relations)

    def test_empty_event_set_ok(self):
        g = OCDCRGraph()
        g.group_top_level_events_into_unspawned_object(set(), "Ghost")
        self.assertIn("Ghost", g.objects)
        self.assertEqual(len(g.objects["Ghost"].events), 0)

class TestOCDCRRelation(unittest.TestCase):
    def setUp(self):
        self.event1 = Event("Activity1")
        self.event2 = Event("Activity2")
        
    def test_relation_creation(self):
        relation = OCDCRRelation(start_event=self.event1,target_event=self.event2,type=RelationTyps.R,quantifier_head=True,quantifier_tail=False)
        
        self.assertEqual(relation.start_event, self.event1)
        self.assertEqual(relation.target_event, self.event2)
        self.assertEqual(relation.type, RelationTyps.R)
        self.assertTrue(relation.quantifier_head)
        self.assertFalse(relation.quantifier_tail)#

    def test_get_quantifiers(self):
        """Test the get_quantifiers method for OCDCRRelation"""
        # Create test events
        event1 = Event("Activity1")
        event2 = Event("Activity2")
        
        # Test case 1: No quantifiers 
        relation1 = OCDCRRelation(event1, event2, RelationTyps.R, False, False)
        self.assertEqual(relation1.get_quantifiers(), (False, False))
        
        # Test case 2: Head quantifier only
        relation2 = OCDCRRelation(event1, event2, RelationTyps.I, True, False)
        self.assertEqual(relation2.get_quantifiers(), (True, False))
        
        # Test case 3: Tail quantifier only
        relation3 = OCDCRRelation(event1, event2, RelationTyps.C, False, True)
        self.assertEqual(relation3.get_quantifiers(), (False, True))
        
        # Test case 4: Both quantifiers
        relation4 = OCDCRRelation(event1, event2, RelationTyps.E, True, True)
        self.assertEqual(relation4.get_quantifiers(), (True, True))
        
        # Test case 5: Verify quantifiers don't affect relation type
        relation5 = OCDCRRelation(event1, event2, RelationTyps.R, True, False)
        self.assertEqual(relation5.type, RelationTyps.R)  # Type should remain unchanged


if __name__ == '__main__':
    unittest.main()

