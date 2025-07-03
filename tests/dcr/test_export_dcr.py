import unittest
import xml.etree.ElementTree as ET
import os

from ocpa.objects.oc_dcr_graph import DCRGraph, RelationTyps, MarkingTyps

class TestDCRGraphExport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Build the graph
        graph = DCRGraph()

        graph.add_event('Event1')
        graph.add_event('Event2', isGroup=True)
        graph.add_event('Event3', parent='Event2')
        graph.add_event('Event4', isGroup=True, parent='Event2')
        graph.add_event('Event5', parent='Event4')

        graph.add_event('Event6', {MarkingTyps.P, MarkingTyps.I})
        graph.add_event('Event7', {MarkingTyps.I}, isGroup=True)
        graph.add_event('Event8', marking={MarkingTyps.P}, parent='Event7')

        graph.add_relation('Event6', 'Event1', RelationTyps.C)
        graph.add_relation('Event7', 'Event2', RelationTyps.R)
        graph.add_relation('Event8', 'Event1', RelationTyps.I)
        graph.add_relation('Event1', 'Event4', RelationTyps.E)

        # Export to XML
        cls.filename = 'test_ocdcr_export.xml'
        graph.export_as_xml(cls.filename, 'Test DCR Export')

        # from ocpa.visualization.oc_dcr_vis import apply, view
        # view(apply(graph))

        # Parse exported XML
        cls.tree = ET.parse(cls.filename)
        cls.root = cls.tree.getroot()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.filename):
            os.remove(cls.filename)

    def test_event_structure(self):
        events = self.root.find('.//resources/events')
        self.assertIsNotNone(events.find("./event[@id='Event2']"))
        self.assertIsNotNone(events.find("./event[@id='Event2']/event[@id='Event3']"))
        self.assertIsNotNone(events.find("./event[@id='Event2']/event[@id='Event4']"))
        self.assertIsNotNone(events.find("./event[@id='Event2']/event[@id='Event4']/event[@id='Event5']"))

        self.assertIsNotNone(events.find("./event[@id='Event7']/event[@id='Event8']"))

    def test_constraints(self):
        conditions = self.root.find('.//constraints/conditions')
        responses = self.root.find('.//constraints/responses')
        includes = self.root.find('.//constraints/includes')
        excludes = self.root.find('.//constraints/excludes')

        self.assertIsNotNone(
            conditions.find("./condition[@sourceId='Event6'][@targetId='Event1']"),
            "Missing expected condition"
        )
        self.assertIsNotNone(
            responses.find("./response[@sourceId='Event7'][@targetId='Event2']"),
            "Missing expected response"
        )
        self.assertIsNotNone(
            includes.find("./include[@sourceId='Event8'][@targetId='Event1']"),
            "Missing expected include"
        )
        self.assertIsNotNone(
            excludes.find("./exclude[@sourceId='Event1'][@targetId='Event4']"),
            "Missing expected exclude"
        )

    def test_runtime_marking(self):
        marking = self.root.find('.//runtime/marking')
        included = {e.attrib['id'] for e in marking.find('included').findall('event')}
        pending = {e.attrib['id'] for e in marking.find('pendingResponses').findall('event')}

        expected_included = {'Event1', 'Event2', 'Event3', 'Event4', 'Event5', 'Event6', 'Event7'}
        expected_pending = {'Event6', 'Event8'}

        self.assertTrue(expected_included.issubset(included),
                        f'Missing included events: {expected_included - included}')
        self.assertTrue(expected_pending.issubset(pending),
                        f'Missing pending response events: {expected_pending - pending}')


if __name__ == '__main__':
    unittest.main()

