'''
    Exports DCR Graphs to XML standart defined in the following paper

    Slaats, Tijs & Mukkamala, Raghava Rao & Hildebrandt, Thomas & Marquard, Morten. (2013). Exformatics Declarative Case Management Workflows as DCR Graphs. 339-354. 10.1007/978-3-642-40176-3_28.

    which is linked in the following book

    Marquard et al. "Web-Based Modelling and Collaborative Simulation of Declarative Processes" https://doi.org/10.1007/978-3-319-23063-4_15
'''
from copy import deepcopy

from lxml import etree
from graphlib import TopologicalSorter

from ocpa.objects.oc_dcr_graph import DCRGraph, RelationTyps, MarkingTyps

def export_dcr_xml(graph:DCRGraph, output_file_name, dcr_title='DCR graph from ocpa'):
    """
        Exports a DCRGraph to a XML file.

        This function generates a DCR XML representation of the input graph, including
        its structure (events, labels, label mappings), relations (conditions, responses,
        includes, excludes), and marking state (executed, included, pending responses).
        It preserves event hierarchy of nested groups.

        Parameters:
            graph (DCRGraph): The graph to export, which will be deep-copied to avoid side effects
            output_file_name (str): Path to the XML file to be written
            dcr_title (str, optional): Title attribute for the DCR graph. Defaults to 'DCR graph from ocpa'
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

    runtime = etree.SubElement(root, "runtime")
    marking = etree.SubElement(runtime, "marking")
    executed = etree.SubElement(marking, "executed")
    included = etree.SubElement(marking, "included")
    pendingResponse = etree.SubElement(marking, "pendingResponses")

    ts = TopologicalSorter(graph.nestedgroups)

    ordered = tuple(ts.static_order())[::-1]
    all_events = ordered + tuple(e for e in graph.events if e not in ordered)

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

    # Add relations
    relation_xml = {
        RelationTyps.I: (includes, "include"),
        RelationTyps.E: (excludes, "exclude"),
        RelationTyps.R: (responses, "response"),
        RelationTyps.C: (conditions, "condition")
    }

    for r in graph.relations:
        xml_parent, xml_tag = relation_xml[r.type]
        xml_rule = etree.SubElement(xml_parent, xml_tag)
        xml_rule.set("sourceId", r.start_event.activity)
        xml_rule.set("targetId", r.target_event.activity)

    for event in graph.marking.get_set(MarkingTyps.E):
        marking_exec = etree.SubElement(executed, "event")
        marking_exec.set("id", event.activity)
    for event in graph.marking.get_set(MarkingTyps.I):
        marking_incl = etree.SubElement(included, "event")
        marking_incl.set("id", event.activity)
    for event in graph.marking.get_set(MarkingTyps.P):
        marking_pend = etree.SubElement(pendingResponse, "event")
        marking_pend.set("id", event.activity)

    tree = etree.ElementTree(root)
    tree.write(output_file_name, pretty_print=True)

