import unittest
import xml.etree.ElementTree as ET
import os

from ocpa.objects.oc_dcr_graph import OCDCRGraph, RelationTyps, MarkingTyps, OCDCRObject, Event

class TestOCDCRXML(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Build the graph
        graph = OCDCRGraph()

        graph.add_event('Event1')
        graph.add_event('Event2', isGroup=True)
        graph.add_event('Event3', parent='Event2')
        graph.add_event('Event4', isGroup=True, parent='Event2')
        graph.add_event('Event5', parent='Event4')

        order_obj = OCDCRObject(spawn=Event('Create1'), type='Object1')
        order_obj.add_event('Object1_Event1', {MarkingTyps.P, MarkingTyps.I})
        order_obj.add_event('Object1_Event2', {MarkingTyps.I}, isGroup=True)
        order_obj.add_event('Object1_Event3', marking={MarkingTyps.P}, parent='Object1_Event2')
        order_obj.add_relation('Object1_Event1', 'Object1_Event2', RelationTyps.C, True, True)
        graph.add_object(order_obj)

        object2 = OCDCRObject(spawn=Event('Create2'), type='Object2')
        object2.add_event('Object2_Event1', {MarkingTyps.P})
        graph.add_object(object2)

        graph.add_relation('Object2_Event1', 'Object1_Event2', RelationTyps.R, True, True)

        # Export to XML
        cls.filename = 'test_ocdcr_export.xml'
        graph.export_as_xml(cls.filename)

        #from ocpa.visualization.oc_dcr_vis import apply, view
        #view(apply(graph))

        # Parse exported XML
        cls.tree = ET.parse(cls.filename)
        cls.root = cls.tree.getroot()

    @classmethod
    def tearDownClass(cls):
        # Clean up the exported file
        if os.path.exists(cls.filename):
            os.remove(cls.filename)

    def test_event_hierarchy_structure(self):
        events = self.root.find('.//resources/events')
        event2 = events.find('./event[@id=\'Event2\']')
        self.assertIsNotNone(event2, 'Event2 should exist')
        self.assertIsNotNone(event2.find('./event[@id=\'Event3\']'), 'Event3 should be a child of Event2')
        event4 = event2.find('./event[@id=\'Event4\']')
        self.assertIsNotNone(event4, 'Event4 should be a child of Event2')
        self.assertIsNotNone(event4.find('./event[@id=\'Event5\']'), 'Event5 should be a child of Event4')

        obj_event2 = events.find('./event[@id=\'Object1_Event2\']')
        self.assertIsNotNone(obj_event2, 'Object1_Event2 should exist')
        self.assertIsNotNone(obj_event2.find('./event[@id=\'Object1_Event3\']'),
                             'Object1_Event3 should be child of Object1_Event2')

    def test_constraints_conditions_and_responses(self):
        conditions = self.root.find('.//constraints/conditions')
        responses = self.root.find('.//constraints/responses')

        condition = conditions.find('./condition[@sourceId=\'Object1_Event1\'][@targetId=\'Object1_Event2\']')
        self.assertIsNotNone(condition, 'Expected condition relation missing')

        response = responses.find('./response[@sourceId=\'Object2_Event1\'][@targetId=\'Object1_Event2\']')
        self.assertIsNotNone(response, 'Expected response relation missing')

    def test_marking_pending_and_included(self):
        marking = self.root.find('.//runtime/marking')
        included_ids = {e.attrib['id'] for e in marking.find('included').findall('event')}
        pending_ids = {e.attrib['id'] for e in marking.find('pendingResponses').findall('event')}

        expected_included = {
            'Object1_Event2', 'Create2', 'Event5', 'Event2',
            'Event3', 'Event4', 'Event1', 'Create1', 'Object1_Event1'
        }
        expected_pending = {
            'Object1_Event1', 'Object2_Event1', 'Object1_Event3'
        }

        self.assertTrue(expected_included.issubset(included_ids),
                        f'Missing included events: {expected_included - included_ids}')
        self.assertTrue(expected_pending.issubset(pending_ids),
                        f'Missing pending events: {expected_pending - pending_ids}')


if __name__ == '__main__':
    unittest.main()
