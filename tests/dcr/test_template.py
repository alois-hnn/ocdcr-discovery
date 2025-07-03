import unittest

from ocpa.objects.oc_dcr_graph import DCRGraph, OCDCRGraph, OCDCRObject, Event, RelationTyps, MarkingTyps
import ocpa.visualization.oc_dcr_vis.visualizer as viz

class TestDCRGraphStringRepresentation(unittest.TestCase):

    def setUp(self):
        self.graph = DCRGraph()

        self.graph.add_event('Event1')
        self.graph.add_event('Event2', isGroup=True)
        self.graph.add_event('Event3', parent='Event2')
        self.graph.add_event('Event4', isGroup=True, parent='Event2')
        self.graph.add_event('Event5', parent='Event4')

        self.graph.add_event('Event6', {MarkingTyps.P, MarkingTyps.I})
        self.graph.add_event('Event7', {MarkingTyps.I}, isGroup=True)
        self.graph.add_event('Event8', marking={MarkingTyps.P}, parent='Event7')

        self.graph.add_relation('Event6', 'Event1', RelationTyps.C)
        self.graph.add_relation('Event7', 'Event2', RelationTyps.C)
        self.graph.add_relation('Event7', 'Event2', RelationTyps.R)
        self.graph.add_relation('Event8', 'Event1', RelationTyps.R)
        self.graph.add_relation('Event8', 'Event1', RelationTyps.I)
        self.graph.add_relation('Event1', 'Event4', RelationTyps.I)
        self.graph.add_relation('Event8', 'Event1', RelationTyps.E)
        self.graph.add_relation('Event1', 'Event4', RelationTyps.E)

        self.string_representation = eval(str(self.graph))  # Convert string back to dict

    def test_events_exist(self):
        expected_events = {'Event1', 'Event2', 'Event3', 'Event4', 'Event5', 'Event6', 'Event7', 'Event8'}
        self.assertEqual(set(self.string_representation['events']), expected_events)

    def test_marking(self):
        self.assertEqual(set(self.string_representation['marking']['pending']), {'Event6', 'Event8'})
        self.assertIn('Event1', self.string_representation['marking']['included'])

    def test_conditions(self):
        self.assertIn('Event1', self.string_representation['conditionsFor'])
        self.assertIn('Event2', self.string_representation['conditionsFor'])
        self.assertIn('Event6', self.string_representation['conditionsFor']['Event1'])

    def test_responses(self):
        self.assertIn('Event7', self.string_representation['responseTo'])
        self.assertIn('Event2', self.string_representation['responseTo']['Event7'])

    def test_includes_and_excludes(self):
        self.assertIn('Event1', self.string_representation['includesTo'])
        self.assertIn('Event4', self.string_representation['includesTo']['Event1'])

        self.assertIn('Event8', self.string_representation['excludesTo'])
        self.assertIn('Event1', self.string_representation['excludesTo']['Event8'])

    def test_nested_groups(self):
        self.assertEqual(self.string_representation['nestedgroups']['Event2'], {'Event3', 'Event4'})
        self.assertEqual(self.string_representation['nestedgroups']['Event4'], {'Event5'})
        self.assertEqual(self.string_representation['nestedgroups']['Event7'], {'Event8'})


class TestOCDCRGraphStringRepresentation(unittest.TestCase):

    def setUp(self):
        self.graph = OCDCRGraph()

        # Add base events
        self.graph.add_event('Event1')
        self.graph.add_event('Event2', isGroup=True)
        self.graph.add_event('Event3', parent='Event2')
        self.graph.add_event('Event4', isGroup=True, parent='Event2')
        self.graph.add_event('Event5', parent='Event4')

        # Add Object1 with internal events and relations
        order_obj = OCDCRObject(spawn=Event('Create1'), type='Object1')
        order_obj.add_event('Object1_Event1', {MarkingTyps.P, MarkingTyps.I})
        order_obj.add_event('Object1_Event2', {MarkingTyps.E}, isGroup=True)
        order_obj.add_event('Object1_Event3', marking={MarkingTyps.P}, parent='Object1_Event2')
        order_obj.add_relation('Object1_Event1', 'Object1_Event2', RelationTyps.C, False, False)
        order_obj.add_relation('Object1_Event1', 'Object1_Event2', RelationTyps.I, True, True)
        self.graph.add_object(order_obj)

        self.graph.add_relation('Event1', 'Event2', RelationTyps.E)
        self.graph.add_relation('Event1', 'Event2', RelationTyps.R)
        self.graph.add_relation('Event1', 'Event2', RelationTyps.I)
        self.graph.add_relation('Event1', 'Event2', RelationTyps.C)


        # Add Object2
        object2 = OCDCRObject(spawn=Event('Create2'), type='Object2')
        object2.add_event('Object2_Event1', {MarkingTyps.P})
        self.graph.add_object(object2)

        # Add inter-object relations
        self.graph.add_relation('Object2_Event1', 'Object1_Event2', RelationTyps.R, True, True)
        self.graph.add_relation('Object2_Event1', 'Object1_Event2', RelationTyps.C, True, True)
        self.graph.add_relation('Object2_Event1', 'Object1_Event2', RelationTyps.I, True, True)
        self.graph.add_relation('Object2_Event1', 'Object1_Event2', RelationTyps.E, True, True)

        # Convert to dictionary for easy assertions
        self.graph_dict = eval(str(self.graph))

    def test_events(self):
        self.assertIn('Event1', self.graph_dict['events'])
        self.assertIn('Object2_Event1', self.graph_dict['events'])

    def test_marking(self):
        self.assertEqual(self.graph_dict['marking']['executed'], {'Object1_Event2'})
        self.assertIn('Object1_Event1', self.graph_dict['marking']['pending'])
        self.assertIn('Create1', self.graph_dict['marking']['included'])

    def test_includes_to(self):
        self.assertIn(('Event2', False, False), self.graph_dict['includesTo'].get('Event1', set()))
        self.assertIn(('Object1_Event2', True, True), self.graph_dict['includesTo'].get('Object1_Event1', set()))

    def test_excludes_to(self):
        self.assertIn(('Event2', False, False), self.graph_dict['excludesTo'].get('Event1', set()))
        self.assertIn(('Object2_Event1', True, True), self.graph_dict['excludesTo'].get('Object1_Event2', set()))

    def test_response_to(self):
        self.assertIn(('Event2', False, False), self.graph_dict['responseTo'].get('Event1', set()))
        self.assertIn(('Object2_Event1', True, True), self.graph_dict['responseTo'].get('Object1_Event2', set()))

    def test_conditions_for(self):
        self.assertIn(('Event1', False, False), self.graph_dict['conditionsFor'].get('Event2', set()))
        self.assertIn(('Object1_Event1', False, False), self.graph_dict['conditionsFor'].get('Object1_Event2', set()))
        self.assertIn(('Object2_Event1', True, True), self.graph_dict['conditionsFor'].get('Object1_Event2', set()))

    def test_nested_groups(self):
        self.assertEqual(self.graph_dict['nestedgroups']['Event2'], {'Event3', 'Event4'})
        self.assertEqual(self.graph_dict['nestedgroups']['Event4'], {'Event5'})
        self.assertEqual(self.graph_dict['nestedgroups']['Object1_Event2'], {'Object1_Event3'})

    def test_objects(self):
        self.assertEqual(self.graph_dict['objects']['Object1'], {'Object1_Event1', 'Object1_Event2', 'Object1_Event3'})
        self.assertEqual(self.graph_dict['objects']['Object2'], {'Object2_Event1'})

    def test_spawn_relations(self):
        self.assertIn('Object1', self.graph_dict['spawnRelations'].get('Create1', set()))
        self.assertIn('Object2', self.graph_dict['spawnRelations'].get('Create2', set()))

if __name__ == '__main__':
    unittest.main()