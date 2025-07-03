'''
    Exports object centric DCR graphs to XML based on an extension of the standard in the following paper, in order to specify the object centric features of the DCR graph

    Slaats, Tijs & Mukkamala, Raghava Rao & Hildebrandt, Thomas & Marquard, Morten. (2013). Exformatics Declarative Case Management Workflows as DCR Graphs. 339-354. 10.1007/978-3-642-40176-3_28.

    which is linked in the following book

    Marquard et al. "Web-Based Modelling and Collaborative Simulation of Declarative Processes" https://doi.org/10.1007/978-3-319-23063-4_15
'''
from copy import deepcopy

from lxml import etree
from graphlib import TopologicalSorter

from ocpa.objects.oc_dcr_graph import OCDCRGraph, RelationTyps, MarkingTyps, DCRGraph

def order(graph: DCRGraph):
    ts = TopologicalSorter(graph.nestedgroups)

    ordered = tuple(ts.static_order())[::-1]
    return ordered + tuple(e for e in graph.events if e not in ordered)


def export_ocdcr_xml(graph:OCDCRGraph, output_file_name, dcr_title='OCDCR graph from ocpa'):
    """
        Exports an OCDCRGraph to an XML file.

        Parameters:
            graph (OCDCRGraph): The object-centric DCR graph to export
            output_file_name (str): Path to the XML file to be written
            dcr_title (str, optional): Title to assign to the XML root element
    """

    graph = deepcopy(graph)

    root = etree.Element("dcrgraph")
    if dcr_title:
        root.set("title", dcr_title)
    specification = etree.SubElement(root, "specification")
    resources = etree.SubElement(specification, "resources")
    events = etree.SubElement(resources, "events")
    labels = etree.SubElement(resources, "labels")
    labelMappings = etree.SubElement(resources, "labelMappings")

    constraints = etree.SubElement(specification, "constraints")
    conditions = etree.SubElement(constraints, "conditions")
    responses = etree.SubElement(constraints, "responses")
    excludes = etree.SubElement(constraints, "excludes")
    includes = etree.SubElement(constraints, "includes")

    spawns = etree.SubElement(specification, "spawns")
    objects = etree.SubElement(specification, "objects")
    object_mappings = etree.SubElement(specification, "object_mappings")

    runtime = etree.SubElement(root, "runtime")
    marking = etree.SubElement(runtime, "marking")
    executed = etree.SubElement(marking, "executed")
    included = etree.SubElement(marking, "included")
    pendingResponse = etree.SubElement(marking, "pendingResponses")

    ts = TopologicalSorter(graph.nestedgroups)

    all_events = order(graph)

    all_relations = set(graph.relations)
    all_relations.update(graph.sync_relations)

    sub_marking_e = set()
    sub_marking_p = set()
    sub_marking_i = set()

    for o in graph.objects:
        xml_object = etree.SubElement(objects, 'object')
        xml_object.set("objectId", o)

        all_events = all_events + order(graph.get_object_graph(o))

        all_relations.update(graph.get_object_graph(o).relations)

        sub_marking_e.update(graph.get_object_graph(o).marking.get_set(MarkingTyps.E))
        sub_marking_p.update(graph.get_object_graph(o).marking.get_set(MarkingTyps.P))
        sub_marking_i.update(graph.get_object_graph(o).marking.get_set(MarkingTyps.I))


    parent_roots = dict()

    for event in all_events:

        if event.parent is not None:
            xml_event = etree.SubElement(parent_roots[event.parent.activity], "event")
        else:
            xml_event = etree.SubElement(events, "event")

        xml_event.set("id", event.activity)

        xml_label = etree.SubElement(labels, "label")
        xml_label.set("id", event.activity)

        xml_labelMapping = etree.SubElement(labelMappings, "labelMapping")
        xml_labelMapping.set("eventId", event.activity)
        xml_labelMapping.set("labelId", event.activity)

        parent_roots[event.activity] = xml_event

    for event, object in graph.activityToObject.items():
        objectmapping = etree.SubElement(object_mappings, "objectMapping")
        objectmapping.set("eventId", event.activity)
        objectmapping.set("objectId", object)


    # Add relations
    relation_xml = {
        RelationTyps.I: (includes, "include"),
        RelationTyps.E: (excludes, "exclude"),
        RelationTyps.R: (responses, "response"),
        RelationTyps.C: (conditions, "condition")
    }

    for r in all_relations:
        xml_parent, xml_tag = relation_xml[r.type]
        xml_rule = etree.SubElement(xml_parent, xml_tag)
        xml_rule.set("sourceId", r.start_event.activity)
        xml_rule.set("targetId", r.target_event.activity)

    for a1, a2 in graph.spawn_relations.items():
        xml_rule = etree.SubElement(spawns, 'spawn')
        xml_rule.set("sourceId", a1.activity)
        xml_rule.set("targetId", a2)


    for event in graph.marking.get_set(MarkingTyps.E).union(sub_marking_e):
        marking_exec = etree.SubElement(executed, "event")
        marking_exec.set("id", event.activity)
    for event in graph.marking.get_set(MarkingTyps.I).union(sub_marking_i):
        marking_incl = etree.SubElement(included, "event")
        marking_incl.set("id", event.activity)
    for event in graph.marking.get_set(MarkingTyps.P).union(sub_marking_p):
        marking_pend = etree.SubElement(pendingResponse, "event")
        marking_pend.set("id", event.activity)

    tree = etree.ElementTree(root)
    tree.write(output_file_name, pretty_print=True)

