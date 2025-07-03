import logging

from traitlets import Bool

from ocpa.objects.log.ocel import OCEL
from pm4py.objects.log.obj import Event
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from ocpa.objects.oc_dcr_graph import Event, IN_TOP_GRAPH

from .constants import *

@dataclass(unsafe_hash=True)
class DiscoverData:
    """
      Data container for event log context and mappings used in object-centric DCR discovery. Provides simple methods for different data information regarding its attributes.

      Attributes:
          ocel (OCEL): The object-centric event log.
          spawn_mapping: (Dict[str, str]) Maps object types to their spawning activities.
          activities_mapping: (Dict[str, str]) Maps activities to corresponding object types.
    """
    ocel: OCEL
    spawn_mapping: Dict[str, str]  # (Object type : Spawn Event)
    activities_mapping: Dict[str, str]  # (activities : object type)
    # default value None marks all combinations of entity types are derived
    derived_entities: List[Tuple[str,str]] = None
    validate_bool: Bool = True # validation can be deactivated for testing purposes

    def __post_init__(self):
        """
        Performs validation on object types and activity mappings upon initialization.

        Raises:
            ValueError: If object types or mappings are invalid.
        """
        if self.validate_bool:
            validator = ErrorManager(self)
            validator.validate()
        else:
            logging.warning("Validation is deactivated.")


    def set_activity_mapping(self, activity: str, obj_type: str) -> None:
        """
        Adds a new activity-to-object-type mapping or overwrites an existing one.

        :param activity: The name of the activity.
        :param obj_type: The object type associated with the activity.
        """
        self.activities_mapping[activity] = obj_type

    def get_spawn_mapping(self, obj: str) -> str:
        return self.spawn_mapping[obj]

    def get_activities(self) -> Set[str]:
        return set(self.activities_mapping.keys())

    def get_spawn_obj_types(self) -> Set[str]:
        return set(self.spawn_mapping.keys())

    def is_activity_spawn_of_obj(self, activity: str, obj: str) -> bool:
        if obj not in self.spawn_mapping:
            return False
        return self.get_spawn_mapping(obj) == activity

    def get_activity_mapping(self, event: Event | str) -> str:
        """
        Resolves an activity to its mapped object type or special classification.

        :param event: Either an Event instance or activity name.
        :return: Object type or a special token (SPAWN or IN_TOP_GRAPH).
        """
        if isinstance(event, Event):
            event = event.activity

        if event in self.spawn_mapping.values():
            return SPAWN
        else:
            return self.activities_mapping[event]


    def are_derived_entities(self, obj_1: str, obj_2: str) -> bool:
        """
        Checks whether two object types are defined as derived entities of each other.

        Args:
            obj_1: First object type to check
            obj_2: Second object type to check

        Returns:
            True if the two object types are defined as derived entities of each other,
            False otherwise and if no derived entities are defined.
        """
        if self.derived_entities is None:
            return False
        return (obj_1, obj_2) in self.derived_entities or (obj_2, obj_1) in self.derived_entities

    def is_spawn_activity(self, event: str | Event) -> bool:
        """
        Determines if an event represents a spawn activity.

        :param event: Event or activity name.
        :return: True if it is a spawn activity.
        """
        return self.get_activity_mapping(event) == SPAWN

    def is_no_spawn_in_top_level(self, event: Event | str) -> bool:
        """
        Checks if the event is not a spawn and belongs to the top-level graph.

        :param event: Event or activity name.
        :return: True if the event is a top-level non-spawn activity.
        """
        return self.get_activity_mapping(event) == IN_TOP_GRAPH

    def is_top_level_activity(self, event: Event|str) -> bool:
        """
        Checks if the event belongs to the top-level graph.

        :param event: Event or activity name.
        :return: True if the event is a top-level activity.
        """
        return not self.is_from_subgraph(event)

    def is_spawned_obj(self, obj_type: str) -> bool:
        """
        Checks if a given object type is spawned dynamically.

        :param obj_type: Name of the object type.
        :return: True if the object type is spawned.
        """
        return obj_type in self.spawn_mapping.keys()

    def is_from_subgraph(self, event: str | Event) -> bool:
        """
        Determines if the event originates from a subgraph.

        :param event: Event or activity name.
        :return: True if it is part of a spawned object subgraph.
        """
        mapping = self.get_activity_mapping(event)
        return not (mapping == SPAWN or mapping == IN_TOP_GRAPH)

    def get_spawned_activities_of_obj(self, obj: str):
        """
        Retrieves all activities that are spawned by a given object type through the activity mapping.

        Args:
            obj: The object type string identifier to get activities for

        Returns:
            A set of activity names that are mapped to the given object type.
            Returns an empty set if no activities are mapped to this object type.
        """
        return {act for act in self.activities_mapping.keys() if self.get_activity_mapping(act) == obj}

    def is_spawned_obj_type(self, obj_type: str) -> bool:
        return obj_type in self.spawn_mapping.keys()

class ErrorManager:
    """
    Validates the integrity and consistency of the DiscoverData configuration.

    Checks include:
    - Valid object types in mappings
    - Activity-object consistency
    - Derived entity correctness
    - Overlaps and missing elements
    """
    def __init__(self, data: DiscoverData):
        """
        Initializes the ErrorManager with the provided discovery data.

        :param data: The DiscoverData instance to validate.
        """
        self.data = data
        self.logger = logging.getLogger(__name__)

    def validate(self) -> None:
        """
        Runs all validation checks: derived entities, object types, and mapped activities.
        """
        self.validate_derived_entities()
        self.validate_object_types()
        self.validate_mapped_activities()

    def validate_object_types(self) -> None:
        """
        Validates object types used in the spawn mapping.
        Also logs warnings for OCEL object types that are not spawned (unspawned).
        """
        for mapped_object in self.data.get_spawn_obj_types():
            if mapped_object not in self.data.ocel.object_types:
                raise KeyError(f"Object type '{mapped_object}' is no object type in ocel")

        not_mapped_obj_types = set()
        for object_type in self.data.ocel.object_types:
            if object_type not in self.data.spawn_mapping.keys():
                not_mapped_obj_types.add(object_type)

        for object_type in not_mapped_obj_types:
            self.logger.warning(f"Object_type '{object_type}' has no associated spawn activity and will be considerd "
                                f"unspawned.")

    def validate_mapped_activities(self) -> None:
        """
        Validates:
        - That all spawn activities exist in the OCEL log
        - That no activity appears in both spawn and activities mapping
        - That all mapped activities and object types are valid
        - Warns and auto-fixes activities that are unmapped
        """
        # Check if all spawn activities exist
        for obj_type, spawn_act in self.data.spawn_mapping.items():
            if spawn_act not in self.data.ocel.obj.activities:
                raise KeyError(
                    f"Spawn activity '{spawn_act}' for object type '{obj_type}' not found in OCEL activities")

        # Ensure spawn and normal activity mappings do not overlap
        overlap = set(self.data.spawn_mapping.values()) & set(self.data.activities_mapping.keys())
        if overlap:
            raise ValueError(f"Activities cannot appear both in spawn_mapping and activities_mapping: {overlap}")

        # Check activity-object mapping is consistent with OCEL structure
        for activity, obj_type in self.data.activities_mapping.items():
            if obj_type not in self.data.ocel.object_types and obj_type != IN_TOP_GRAPH:
                raise KeyError(f"Object type '{obj_type}' is no object type in ocel")

            if activity not in self.data.ocel.obj.activities:
                raise KeyError(f"Activity '{activity}' is no activity in ocel")

        # Warn and fix unmapped activities
        not_mapped_activities = set()
        for activity in self.data.ocel.obj.activities:
            if activity not in self.data.spawn_mapping.values() and activity not in self.data.activities_mapping.keys():
                not_mapped_activities.add(activity)
        for activity in not_mapped_activities:
            self.logger.warning(f"Activity '{activity}' has no associated object type and will be seen as an top "
                                f"level activity.")
            self.data.activities_mapping[activity] = IN_TOP_GRAPH

    def validate_derived_entities(self) -> None:
        """
        Validates the defined derived entities:
        - Must be pairs of different object types
        - All types must exist in the OCEL object types list
        """
        if self.data.derived_entities is None:
            return
        for obj_type1, obj_type2 in self.data.derived_entities:
            if obj_type1 == obj_type2:
                raise ValueError("Derived Entity Type tupel must contain different types")
            if obj_type1 not in self.data.ocel.object_types:
                raise ValueError(f"Input '{obj_type1}' is not a object type")
            if obj_type2 not in self.data.ocel.object_types:
                raise ValueError(f"Input '{obj_type2}' is not a object type")