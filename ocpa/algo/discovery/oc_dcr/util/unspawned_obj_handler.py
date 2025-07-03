from .discover_data import DiscoverData

from typing import Dict, Set

from ocpa.objects.oc_dcr_graph import OCDCRGraph,Event, IN_TOP_GRAPH


class UnspawnedObjHandler:
    """
    Handles object types that are not spawned by any activity in the OCEL log.

    This class maps activities associated with unspawned objects to the top-level process
    and groups those activities logically in the final OC-DCR graph, since logically activities in unspawned objects
    and in top level graphs are handled exactly the same in OC Discover
    """

    def __init__(self, data: DiscoverData):
        """
        Initializes the handler with DiscoverData and prepares containers for tracking
        unspawned objects and their corresponding activities.

        :param data: The DiscoverData instance containing OCEL and mappings.
        """
        self.data = data
        self.unspawned_obj_activity_map: Dict[str,str] = {}  # (activity: object type)
        self.unspawned_obj: Set[str] = set()

    def create_unspawned_obj_activity_map(self) -> None:
        """
        Identifies all object types in the OCEL log that do not have a spawn activity.
        These types are marked as unspawned for special handling.
        """
        for obj_type in self.data.ocel.object_types:
            if not self.data.is_spawned_obj_type(obj_type):
                self.unspawned_obj.add(obj_type)

    def handle_input_mapping(self) -> None:
        """
        Updates the activity mapping for all activities associated with unspawned
        object types, categorizing them as part of the top-level process.
        """
        for act in self.data.get_activities():
            obj_type = self.data.get_activity_mapping(act)
            if obj_type in self.unspawned_obj:
                self.unspawned_obj_activity_map[act] = obj_type
                self.data.set_activity_mapping(act, IN_TOP_GRAPH)

    def get_all_events_of_obj(self, obj_type: str, oc_dcr: OCDCRGraph) -> Set[Event]:
        """
        Retrieves all event instances from the OC-DCR graph that belong to a given unspawned object type.

        :param obj_type: The name of the unspawned object type.
        :param oc_dcr: The object-centric DCR graph.
        :return: A set of Event objects associated with the object type.
        """
        return {
            oc_dcr.get_event(activity)
            for activity, mapped_obj_type in self.unspawned_obj_activity_map.items()
            if mapped_obj_type == obj_type
        }

    def group_unspawned_obj_activities(self, oc_dcr: OCDCRGraph) -> OCDCRGraph:
        """
        Groups all events associated with unspawned object types into artificial objects
        within the OC-DCR graph for logical separation and clarity.

        :param oc_dcr: The object-centric DCR graph.
        :return: The updated OC-DCR graph with grouped top-level events.
        """
        for obj in self.unspawned_obj:
            events = self.get_all_events_of_obj(obj, oc_dcr)
            oc_dcr.group_top_level_events_into_unspawned_object(events, obj)

        return oc_dcr