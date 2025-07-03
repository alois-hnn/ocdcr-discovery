from .dcr_graph import DCRGraph
from .markings import MarkingTyps
from .relations import DCRRelation, RelationTyps, OCDCRRelation
from .event import Event
from .oc_dcr_object import OCDCRObject

from .constants import IN_TOP_GRAPH

from typing import Set, Dict, Optional

class OCDCRGraph(DCRGraph):
	"""
	Represents an Object-Centric DCR (OCDCR) graph.

	Extends DCRGraph with object-centric capabilities including:
	- Multiple objects with their own subgraphs
	- Spawn relations between events and objects
	- Synchronization relations between objects
	- Quantified relations

	"""

	def __init__(self, dcr: Dict | DCRGraph = None):
		"""
		Initialize an OCDCR graph. It can be initialized with a dcr graph template template:

		dcr_template = {
			'events': set(),
			'marking': {'executed': set(), 'pending': set(),
						'included': set()},
			'includesTo': {},                                   ## {'event1': {'event2', 'event3'}} means that event2 and event3 will be included when event1 executes
			'excludesTo': {},                                   ## {'event1': {'event2', 'event3'}} means that event2 and event3 will be excluded when event1 executes
			'responseTo': {},                                   ## {'event1': {'event2', 'event3'}} means that event2 and event3 are responses to event1
			'conditionsFor': {},                                ## {'event1': {'event2', 'event3'}} means that event2 and event3 are conditions for event1
			'nestedgroups': {},                                 ## {'event1': {'event2', 'event3'}} means that event1 is a nested group including event2 and event3
		}

		Beware that this is without its object subgraphs and sync relations which still have to be added. This can for example be done by add_object.


		Args:
			template: Optional template to initialize from
		"""

		self.__objects: Dict[
			str, OCDCRObject] = dict()  # {(objectID, OCDCRObject)}  Maps object types to their OCDCRObject
		self.__spawn_relations: Dict[Event, str] = dict()  # {(activity, objectID)}  Maps spawn events to object types
		self.__sync_relations: Set[OCDCRRelation] = set()  # Relations between different objects
		self.__activityToObject: Dict[
			Event, str] = dict()  # {(activity, objectID)} Maps events to their object types, IN_TOP_GRAPH if in top graph

		if isinstance(dcr, DCRGraph):
			# Initialize from existing DCRGraph
			self.marking = dcr.marking
			self.relations = dcr.relations
			self.events = dcr.events
			for e in dcr.events:
				self.__activityToObject[e] = IN_TOP_GRAPH
			self.nestedgroups = dcr.nestedgroups
			self.nested_events = dcr.nested_events
		else:
			# Initialize normally with optional template
			super().__init__(dcr)

	@property
	def sync_relations(self) -> Set[OCDCRRelation]:
		return self.__sync_relations

	@sync_relations.setter
	def sync_relations(self, sync_relations: Set[OCDCRRelation]):
		self.__sync_relations = sync_relations

	@property
	def objects(self) -> Dict[str, OCDCRObject]:
		return self.__objects

	@objects.setter
	def objects(self, objects: Dict[str, OCDCRObject]):
		self.__objects = objects

	@property
	def spawn_relations(self) -> Dict[Event, str]:
		return self.__spawn_relations

	@property
	def activityToObject(self) -> Dict[Event, str]:
		self.update_activities()
		return self.__activityToObject

	def add_object(self, obj: OCDCRObject) -> None:
		"""
		Add an object to the graph.

		Args:
			obj: The OCDCR object to add
		"""
		self.__objects[obj.type] = obj

		if obj.spawn is not None:
			self.spawn_relations[obj.spawn] = obj.type
			if self.get_event(obj.spawn.activity) is None:
				self.add_event(obj.spawn.activity)

		for act in obj.events:
			self.__activityToObject[act] = obj.type

	def _add_event_to_top_level(self, activity: str | Event, marking: Set[MarkingTyps] = {MarkingTyps.I},
								isGroup: bool = False, parent: str = None) -> Event:
		"""
		Internal method to add an event to the top-level graph.

		Args:
			activity: The event or activity name to add
			marking: Initial marking for the event (Default: False)
			isGroup: Whether this is a group event (Default: {MarkingTyps.I} ## event is included)
			parent: Optional parent for nested events (Default: None)

		Returns:
			The created or added Event
		"""
		event = super().add_event(activity, marking=marking, isGroup=isGroup, parent=parent)
		if event not in self.activityToObject.keys():
			self.activityToObject[event] = IN_TOP_GRAPH
		return event

	def _add_sync_relation(self, start_event: str, target_event: str,
						   relation_type: RelationTyps, quantifier_head: bool = True,
						   quantifier_tail: bool = True) -> None:
		"""
		Internal method to add a synchronization relation between events in different objects.

		Args:
			start_event: Source event activity name
			target_event: Target event activity name
			relation_type: Type of relation
			quantifier_head: Whether head is quantified (Default: True)
			quantifier_tail: Whether tail is quantified (Default: True)
		"""
		relation = OCDCRRelation(
			start_event=self.get_event(start_event),
			target_event=self.get_event(target_event),
			type=relation_type,
			quantifier_head=quantifier_head,
			quantifier_tail=quantifier_tail,
		)
		self.__sync_relations.add(relation)

	def get_relation(self, start_event: Event, target_event: Event, type: RelationTyps) -> DCRRelation | None:
		"""
		Return a specific edge between two events in the OCDCR graph.

		Searches through:
		1. Main graph relations
		2. Relations within each object's subgraph
		3. Synchronization relations between objects

		Args:
			start_event: The source event of the relation
			target_event: The target event of the relation
			type: The type of relation to search for

		Returns:
			DCRRelation: The matching relation object or None if not found.

		"""

		def matches(r: DCRRelation) -> bool:
			return (
					r.type == type and
					r.start_event.activity == start_event.activity and
					r.target_event.activity == target_event.activity
			)
        # look in all relations
		for r in self.get_all_relations():
			if matches(r):
				return r

		return None

	def add_event(self, activity: str | Event, marking: set[MarkingTyps] = {MarkingTyps.I},
				  isGroup: bool = False, parent: str = None, obj: OCDCRObject | str = None) -> Event:
		"""
		Add an event to the graph, either to a specific object or the top level.

		Args:
			activity: The event or activity name to add
			marking: Initial marking for the event (Default: False)
			isGroup: Whether this is a group event (Default: {MarkingTyps.I} ## event is included)
			parent: Optional parent for nested events (Default: None)
			obj: Optional object or object type to add the event to (Default: None)

		Returns:
			The created or added Event

		Raises:
			ValueError: If the Event already exists
			KeyError: If specified object doesn't exist
		"""

		if self.get_event(activity) is not None:
			raise ValueError("Event '{}' already exists".format(activity))

		if isinstance(obj, OCDCRObject):
			obj = obj.type

		if obj is None:
			event = self._add_event_to_top_level(activity, marking=marking, isGroup=isGroup, parent=parent)
		else:
			if obj not in self.objects.keys():
				raise KeyError(f"{obj}'is not in this OC-DCR Graph ")
			else:
				event = self.objects[obj].add_event(activity, marking=marking, isGroup=isGroup, parent=parent)
				self.activityToObject[event] = obj
		return event

	def add_relation(self, start_event: Event, target_event: Event, relation_type: RelationTyps,
					 quantifier_head: bool = False, quantifier_tail: bool = False) -> None:
		"""
		Add a relation between two events in the OCDCR graph with optional quantifiers.

		Handles three cases:
		1. Both events are in the main graph
		2. Both events are in the same object's subgraph
		3. Events are in different objects

		If the relation already exists, updates its quantifiers instead of creating a new one.

		Args:
			start_event: Source event as Event or str
			target_event: Target event as Event or str
			relation_type: Type of relation to add
			quantifier_head: Whether target is quantified (default: False)
			quantifier_tail: Whether source is quantified (default: False)

		Raises:
			TypeError: If events are not both strings or both Event objects
			ValueError: If either event is not found
		"""
		# Convert string activity names to Event objects if strings
		if isinstance(start_event, str) and isinstance(target_event, str):
			start_event = self.get_event(start_event)
			target_event = self.get_event(target_event)

		if start_event is None or target_event is None:
			raise ValueError("Event not found")

		if not (isinstance(start_event, Event) and isinstance(target_event, Event)):
			raise TypeError("Events must be both strings or both Event objects")

		# Check if relation already exists
		e = self.get_relation(start_event, target_event, relation_type)
		if e is not None:
			# Update quantifiers if relation exists
			e.quantifier_head = quantifier_head
			e.quantifier_tail = quantifier_tail
			return

		# Updates the activities in case some activities changed
		self.update_activities()
		# Decide if edge is a sync relation or normal edge and if it is in top or subgraph
		obj_start = self.activityToObject[start_event]
		obj_target = self.activityToObject[target_event]

		if obj_start == IN_TOP_GRAPH and obj_target == IN_TOP_GRAPH:
			# One or both events in main graph
			self.relations.add(
				OCDCRRelation(start_event, target_event, relation_type, quantifier_head, quantifier_tail))
		elif obj_start == obj_target:
			# Both events are in same object
			self.objects[obj_start].add_relation(start_event, target_event, relation_type, quantifier_head,
												 quantifier_tail)
		else:
			# Events are in different objects
			self._add_sync_relation(start_event.activity, target_event.activity, relation_type, quantifier_head,
									quantifier_tail)

	def get_object_graph(self, obj_type : str) -> OCDCRObject | None:
		"""
		Get the subgraph for a specific object.

		Args:
			obj_type: The type identifier of the object

		Returns:
			The OCDCRObject representing the object's subgraph or None if Top Level
		"""
		if obj_type == IN_TOP_GRAPH:
			return None

		return self.__objects[obj_type]

	def get_events(self) -> Set[Event]:
		"""Get all events in the graph, including those in objects."""
		self.update_activities()
		return set(self.__activityToObject.keys()).union(super().events)

	def get_all_relations(self) -> Set[DCRRelation]:
		"""Get all relations in the graph, including those in objects and sync relations.."""
		all_relations = self.relations.union(self.sync_relations)
		for obj in self.objects.values():
			all_relations = all_relations.union(obj.relations)
		return all_relations

	def get_event(self, event_to_search: str | Event) -> Optional[Event]:
		"""
		Get an event by its activity name, searching across all objects.

		Args:
			event_to_search: The name of the activity or activity to find

		Returns:
			The Event object if found, None otherwise
		"""
		if isinstance(event_to_search, Event):
			event_to_search = event_to_search.activity

		for event in self.get_events():
			if event.activity == event_to_search:
				return event
		return None

	def get_incidental_relations(self, event: Event) -> Set[DCRRelation]:
		"""
		Get all relations connected to a specific event across the entire graph.

		Args:
			event: The event to find relations for

		Returns:
			Set of all relations for the event
		"""
		if self.get_event(event.activity) is None:
			raise KeyError(f"'{event}' not in graph")

		from_relations = {
			edge for target_event in self.activityToObject
			for type in RelationTyps
			if (edge := self.get_relation(event, target_event, type)) is not None
		}

		to_relations = {
			edge for start_event in self.activityToObject
			for type in RelationTyps
			if (edge := self.get_relation(start_event, event, type)) is not None
		}

		return from_relations | to_relations

	def update_activities(self):
		"""
		Update the activityToObject mapping for all activities of all objects.

		Ensures the mapping between events and their containing objects is current.
		"""
		for obj in self.objects.values():
			for act in obj.events:
				self.__activityToObject[act] = obj.type

	def corr(self, a1: Event) -> OCDCRObject | str:
		"""
        Find the object that correlates to the given event.

        Args:
            a1: The event to locate

        Returns:
            The OCDCRObject that contains the event or IN_TOP_GRAPH if in top level.
        Raises:
            KeyError if the event is not in graph
        """
		if a1 not in self.activityToObject.keys():
			raise KeyError(f"'{a1}' not in graph")

		obj_id = self.activityToObject[a1]

		if obj_id != IN_TOP_GRAPH:
			return self.get_object_graph(obj_id)
		else:
			return IN_TOP_GRAPH

	def _spawn(self, a1: Event) -> Event | None:
		"""
        Get the spawn event for the object containing the given event.

        Args:
            a1: The event to locate

        Returns:
            The spawn event of the containing object or None if not found
        """
		ent = self.corr(a1)

		if ent == IN_TOP_GRAPH:
			return None

		return ent.spawn

	def partition(self, relations: Set[DCRRelation]) -> None:
		"""
		Convert relations between events into many-to-many relations
		only if both events are associated with object instances.

		If either event is a top-level (non-object) event, the relation is skipped.
		Otherwise, the relation is added with both quantifiers enabled.

		:parameter: relations (Set[DCRRelation]): A set of DCR relations to process.
		"""
		for relation in relations:
			spawn_start = self._spawn(relation.start_event)
			spawn_target = self._spawn(relation.target_event)

			if not spawn_start or not spawn_target:
				continue

			self.add_relation(
				relation.start_event,
				relation.target_event,
				relation.type,
				quantifier_head=True,
				quantifier_tail=True
			)

	def remove_relation(self, relation: DCRRelation | OCDCRRelation) -> bool:
		"""
		  Remove a relation from the graph, handling all relation types.

		  Args:
			  relation: The relation to remove

		  Returns:
			  bool: True if relation was found and removed, False otherwise

		  Raises:
			  KeyError: If object referenced in relation doesn't exist
		  """

		# Validate relation exists
		if relation not in self.get_all_relations():
			return False

		# Get object mappings safely
		start_obj = self.activityToObject.get(relation.start_event, IN_TOP_GRAPH)
		target_obj = self.activityToObject.get(relation.target_event, IN_TOP_GRAPH)

		# Determine relation location and remove
		if start_obj == IN_TOP_GRAPH and target_obj == IN_TOP_GRAPH:
			# Top-level relation
			self.relations.discard(relation)
		elif start_obj == target_obj:
			# Object-internal relation
			if start_obj in self.objects:
				self.objects[start_obj].relations.discard(relation)
			else:
				raise KeyError(f"Object {start_obj} not found in graph")
		else:
			# Sync relation between objects
			self.sync_relations.discard(relation)

		return True

	def group_top_level_events_into_unspawned_object(self, events: Set[Event], object_type: str) -> None:
		# Validate all events are in the top-level graph
		invalid_events = [event for event in events if self.activityToObject.get(event) != IN_TOP_GRAPH]
		if invalid_events:
			raise KeyError(f"The following events are not in TOP_GRAPH: {invalid_events}")

		# Ensure the object type is not already spawned
		if object_type in self.spawn_relations.values():
			raise KeyError(f"Object type '{object_type}' is already spawned")

		# Create a new unspawned object
		new_object = OCDCRObject(None, object_type)
		self.add_object(new_object)

		incidental_relations = set()

		# Reassign each event to the new object
		for event in events:
			incidental_relations.update(self.get_incidental_relations(event))
			self.remove_event(event)
			self.add_event(activity=event, obj=object_type)

		self.relations.difference_update(incidental_relations)

		for incidental_relation in incidental_relations:
			head, tail = incidental_relation.get_quantifiers()
			self.add_relation(incidental_relation.start_event, incidental_relation.target_event,
							  incidental_relation.type, head, tail)

	def remove_event(self, event: Event) -> None:
		"""
		Remove an event from the OCDCR graph, including all its associated relations.

		This method first removes all incidental (incoming and outgoing) relations of the event.
		Then, it removes the event either from the top-level graph or from the corresponding object subgraph.

		:arg:
			event (Event): The event to be removed.

		:raise:
			ValueError: If event is spawn event
			KeyError: If the event does not exist in the graph.
		"""
		if event in self.spawn_relations.keys():
			raise ValueError(f"'{event}' you cannot remove spawn event")

		if event not in self.activityToObject:
			raise KeyError(f"'{event}' is not part of the graph.")

		obj = self.activityToObject[event]
		# event is in top level
		if obj == IN_TOP_GRAPH:
			super().remove_event(event)
		# event is in subgraph
		else:
			incidental_relations = self.get_incidental_relations(event)
			for relation in incidental_relations:
				self.remove_relation(relation)
			self.get_object_graph(obj).remove_event(event)

		del self.activityToObject[event]

	def export_as_xml(self, output_file_name, dcr_title='OCDCR graph from ocpa') -> None:
		"""Exports the graph to xml file."""
		from ocpa.objects.oc_dcr_graph import export_ocdcr_xml
		export_ocdcr_xml(self, output_file_name=output_file_name, dcr_title=dcr_title)

	def __str__(self) -> str:
		from ocpa.util.dcr.converter import OCDCRConverter
		"""Return a string representation of the graph."""
		return str(OCDCRConverter.to_string_representation(self))