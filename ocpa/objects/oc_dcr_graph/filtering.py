from copy import deepcopy

from ocpa.objects.oc_dcr_graph import DCRGraph, OCDCRGraph, RelationTyps, OCDCRObject


def filter_by_relation_type(dcr: DCRGraph | OCDCRGraph | OCDCRObject, constraint_types: set[RelationTyps]):
    """
        Filters the relations in a DCR-like graph structure based on the specified constraint types.

        This function creates a deep copy of the input graph and removes all relations
        that are not of the types specified in `constraint_types`. For OCDCRGraph instances,
        it also filters the relations of each object in the graph and the sync relations.

        Parameters:
            dcr (DCRGraph | OCDCRGraph | OCDCRObject): The graph or object whose relations are to be filtered
            constraint_types (set[RelationTyps]): A set of relation types to retain in the graph

        Returns:
            A deep-copied version of the input graph or object with only the specified types of relations retained
    """
    g = deepcopy(dcr)
    g.relations = {r for r in g.relations if r.type in constraint_types}

    if isinstance(dcr, OCDCRGraph):
        for k, o in g.objects.items():
            g.objects[k] = filter_by_relation_type(o, constraint_types)
        g.sync_relations = {r for r in g.sync_relations if r.type in constraint_types}

    return g


def filter_many_to_many(dcr: DCRGraph | OCDCRGraph | OCDCRObject, constraint_types = set()):
    """
        Filters out many-to-many quantified relations from a DCR-like graph structure,
        optionally preserving relations of specific types.

        This function removes relations that are identified as many-to-many (i.e., both `quantifier_head` and `quantifier_tail` are True).

        For OCDCRGraph instances, it also filters sync relations and recursively filters the contained objects.

        Parameters:
            dcr : (DCRGraph | OCDCRGraph | OCDCRObject): The graph or object to filter.
            constraint_types (set[RelationTyps]): A set of relation types to retain, regardless of quantifier status.

        Returns:
            A deep-copied version of the input with filtered relations based on the specified rules.
    """
    g = deepcopy(dcr)


    g.relations = {
        r for r in g.relations if (
                    (r.type in constraint_types)
                    or (hasattr(r, "quantifier_head") is False)
                    or (hasattr(r, "quantifier_head") and
                        ((r.quantifier_head and r.quantifier_tail)
                     is False)))
    }

    if isinstance(dcr, OCDCRGraph):

        g.sync_relations = {r for r in g.sync_relations if r.type in constraint_types}
        for k, o in g.objects.items():
            g.objects[k] = filter_many_to_many(o, constraint_types)

    return g

def filter_one_to_many(dcr: DCRGraph | OCDCRGraph | OCDCRObject, constraint_types: set[RelationTyps] = set()):
    """
        Filters out one-to-many quantified relations from a DCR-like graph structure, optionally retaining specific constraint types.

        This function creates a deep copy of the input and removes relations identified as one-to-many.

        For OCDCRGraph instances, it recursively filters the contained objects.

        Parameters:
            dcr (DCRGraph | OCDCRGraph | OCDCRObject): The graph or object whose relations should be filtered.
            constraint_types (set[RelationTyps]): A set of relation types to always retain.

        Returns:
            A deep-copied version of the input graph or object with one-to-many relations filtered out.
    """
    g = deepcopy(dcr)

    g.relations = {
        r for r in g.relations if (
                (r.type in constraint_types)
                or (hasattr(r, "quantifier_head") is False)
                or (hasattr(r, "quantifier_head") and
                    ((r.quantifier_head or r.quantifier_tail)
                     is False) and ((r.quantifier_head and r.quantifier_tail) is False)))
    }

    if isinstance(dcr, OCDCRGraph):
        g.sync_relations = {
            r for r in g.sync_relations if (
                    (r.type in constraint_types)
                    or (hasattr(r, "quantifier_head") is False)
                    or (hasattr(r, "quantifier_head") and
                        ((r.quantifier_head or r.quantifier_tail)
                         is False) and ((r.quantifier_head and r.quantifier_tail) is False)))
        }
        for k, o in g.objects.items():
            g.objects[k] = filter_one_to_many(o, constraint_types)


    return g