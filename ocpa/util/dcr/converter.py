import ocpa.objects.oc_dcr_graph as dcr
from typing import Dict
from copy import deepcopy

# Templates representing the structure of DCR and OCDCR graphs.
# These are used for graph representations as dicts.
dcr_template = {
    'events': set(),
    'marking': {'executed': set(), 'pending': set(), 'included': set()},
    'includesTo': {},
    'excludesTo': {},
    'responseTo': {},
    'conditionsFor': {},
    'nestedgroups': {}
}

ocdcr_template = {
    'events': set(),
    'marking': {'executed': set(), 'pending': set(), 'included': set()},
    'includesTo': {},
    'excludesTo': {},
    'responseTo': {},
    'conditionsFor': {},
    'nestedgroups': {},
    'objects': {},
    'spawnRelations': {}
}

class DCRConverter:
    """
    A utility class to handle conversion between DCRGraph objects and their dictionary-based template representations.
    """

    @staticmethod
    def _get_marking(template, graph: dcr.OCDCRGraph) -> dcr.DCRMarking:
        """
        Converts marking template into a DCRMarking object.
        """
        marking = dcr.DCRMarking()
        # Add executed events
        for activity in template['marking']['executed']:
            marking.add_event(graph.get_event(activity), dcr.MarkingTyps.E)
        # Add included events
        for activity in template['marking']['included']:
            marking.add_event(graph.get_event(activity), dcr.MarkingTyps.I)
        # Add pending events
        for activity in template['marking']['pending']:
            marking.add_event(graph.get_event(activity), dcr.MarkingTyps.P)
        return marking

    @staticmethod
    def _iterate_through_relation_temp(graph: dcr.DCRGraph, relation_dict: Dict, typ: dcr.RelationTyps) -> None:
        """
        Adds relations of a specific type to a DCR graph based on the dictionary format.
        """
        for target, start_events in relation_dict.items():
            for start in start_events:
                # Conditions are treated in the other direction
                if typ == dcr.RelationTyps.C:
                    graph.add_relation(start, target, typ)
                else:
                    graph.add_relation(target, start, typ)

    @staticmethod
    def graph_from_template(graph: dcr.DCRGraph, template):
        """
        Converts a template dictionary to it's dcr graph representation.
        """
        # Add events
        for event in template['events']:
            graph.add_event(event, marking=set())

        # Set marking
        graph.marking = DCRConverter._get_marking(template, graph)

        # Add all relation types
        for typ in dcr.RelationTyps:
            DCRConverter._iterate_through_relation_temp(graph, template.get(typ.value, {}), typ)

        # Add nested group relations
        graph.nestedgroups = {
            graph.get_event(parent_activity): {graph.get_event(child_activity) for child_activity in val}
            for parent_activity, val in template.get('nestedgroups', {}).items()
        }

        for nested_event in graph.nestedgroups:
            graph.nested_events.add(nested_event)

    @staticmethod
    def to_string_representation(graph: dcr.DCRGraph):
        """
        Converts a DCRGraph object into a template dictionary.
        """
        template = deepcopy(dcr_template)

        # Add events
        for event in graph.events:
            template['events'].add(event.activity)

        # Add markings
        for typ in dcr.MarkingTyps:
            template['marking'][typ.value] = {e.activity for e in graph.marking.get_set(typ)}

        # Add relations
        for relation in graph.relations:
            if isinstance(relation, dcr.OCDCRRelation):
                # Handle object-centric relations with quantifiers
                if relation.type == dcr.RelationTyps.C:
                    template[relation.type.value].setdefault(relation.target_event.activity, set()).add(
                        (relation.start_event.activity, relation.quantifier_head, relation.quantifier_tail))
                else:
                    template[relation.type.value].setdefault(relation.start_event.activity, set()).add(
                        (relation.target_event.activity, relation.quantifier_head, relation.quantifier_tail))
            else:
                # Standard DCR relations
                if relation.type == dcr.RelationTyps.C:
                    template[relation.type.value].setdefault(relation.target_event.activity, set()).add(
                        relation.start_event.activity)
                else:
                    template[relation.type.value].setdefault(relation.start_event.activity, set()).add(
                        relation.target_event.activity)

        # Add nested group structure
        for group, val in graph.nestedgroups.items():
            for event in val:
                template['nestedgroups'].setdefault(group.activity, set()).add(event.activity)

        return template

    @staticmethod
    def import_graph(template) -> dcr.DCRGraph:
        """
        Constructs a DCRGraph object from its dictionary template representation.
        """
        graph = dcr.DCRGraph()
        DCRConverter.graph_from_template(graph, template)
        return graph


class OCDCRConverter:
    """
    Handles conversion between Object-Centric DCR (OCDCR) graphs and their dictionary-based template representations,
    extending the functionality provided by DCRConverter.
    """

    @staticmethod
    def deep_merge(d1, d2):
        """
        Recursively merges dictionary d1 into d2 to combining graph templates.
        """
        from collections.abc import Mapping
        for k, v in d1.items():
            if k in d2:
                if isinstance(d2[k], Mapping) and isinstance(v, Mapping):
                    OCDCRConverter.deep_merge(v, d2[k])
                elif isinstance(d2[k], set) and isinstance(v, set):
                    d2[k].update(v)  # union sets
            else:
                d2[k] = v  # add missing keys
        return d2

    @staticmethod
    def to_string_representation(graph: dcr.OCDCRGraph):
        """
        Converts an OCDCRGraph object to a dictionary template.
        Includes object structure and spawn relations.
        """
        template = deepcopy(ocdcr_template)

        # Convert core DCR part
        dcr_temp = DCRConverter.to_string_representation(graph)
        OCDCRConverter.deep_merge(dcr_temp, template)

        # Handle individual object graphs
        for key, obj in graph.objects.items():
            template['objects'].setdefault(key, set())
            obj_template = DCRConverter.to_string_representation(obj)

            template['objects'][key].update(obj_template['events'])
            OCDCRConverter.deep_merge(obj_template, template)

            if obj.spawn is not None:
                # Add spawn relations
                template['spawnRelations'].setdefault(obj.spawn.activity, set()).add(key)

        # Handle synchronization relations
        for r in graph.sync_relations:
            template[r.type.value].setdefault(r.target_event.activity, set()).add(
                (r.start_event.activity, r.quantifier_head, r.quantifier_tail))

        return template
