from ocpa.objects.log.ocel import OCEL

from typing import Dict, List, Set, Tuple

from ocpa.objects.oc_dcr_graph import OCDCRGraph
from .util import Discover



def apply(ocel: OCEL, spawn_mapping: Dict[str, str], activities_mapping: Dict[str, str], apply_nested = False, derived_entities: List[Tuple[str,str]] = None) \
        -> OCDCRGraph:
    """
    Applies the OC-DCR discovery algorithm on an object-centric event log.

    This function initializes the discovery pipeline and returns the complete object-centric dcr graph, optionally applying nesting to subgraphs. For nesting, only the one to one relations will be considered.
    If given, the resulting graph will filter only the many to many relations between derived entities, otherwise it will treat all possible combinations as derived.
    Derived entities are pairs of object types that are considered to have interesting interplay.

    Args:
        ocel (OCEL): The input Object-Centric Event Log.
        spawn_mapping (Dict[str, str]): Maps each object type to the activity that spawns it, if an object does not appear, it will be treated as unspawned.
        activities_mapping (Dict[str, str]): Maps each activity to its corresponding object type, if an activity does not appear, it will be treated as a top level graph activity.
        apply_nested (bool, optional): If True, nested subgraphs will be created.
        derived_entities (List[Tuple[str, str]], optional): Pairs of object types that are considered to have interesting interplay for many-to-many synchronization discovery.

    Returns:
        OCDCRGraph: The final discovered ocdcr graph.
    """
    discover = Discover(ocel=ocel, spawn_mapping=spawn_mapping, activities_mapping=activities_mapping, apply_nested = apply_nested,
                        derived_entities=derived_entities)
    return discover.apply()
