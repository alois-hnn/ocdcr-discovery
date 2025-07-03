from typing import Set, Dict, Optional
import copy

from .markings import DCRMarking, MarkingTyps
from .relations import DCRRelation, RelationTyps
from .event import Event



class DCRGraph:
	"""
	Represents a Dynamic Condition Response (DCR) Graph.

	A DCR graph consists of:
	- Events: The nodes of the graph representing activities
	- Relations: The edges between events defining constraints
	- Marking: The current state of the graph representing which events are executed/included/pending
	- Nested groups: Hierarchical grouping of events

	"""

	def __init__(self, template=None):
		"""
		Initialize a DCR graph. It can be initialized with the following dcr_template:
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

		Args:
			template: Optional template to initialize the graph from


		"""
		self.__marking = DCRMarking()
		self.__relations: Set[DCRRelation] = set()
		self.__events: Set[Event] = set()
		self.__nestedgroups: Dict[Event, Set[Event]] = {}
		self.__nested_events: Set[Event] = set()

		if template is not None:
			from ocpa.util.dcr.converter import DCRConverter
			DCRConverter.graph_from_template(self, template)

		for g, children in self.nestedgroups.items():
			g.isGroup = True
			for child in children:
				child.parent = g

	@classmethod
	def from_attributes(cls, events: Set[Event], relations: Set[DCRRelation], marking: DCRMarking,
						nested_groups: Dict[Event, Set[Event]], nested_events: Set[Event]) -> 'DCRGraph':

		"""
		Create a DCRGraph by initializing it with given components.


		Args:
			events: Set of Event objects to include in the graph.
			relations: Set of DCRRelation objects defining the structure.
			marking: DCRMarking representing the execution state.
			nested_groups: Dictionary mapping group events to child events.
			nested_events: Set of Events that belong to any group.

		Returns:
			A new DCRGraph instance based on the provided components.
		"""
		graph = cls()
		graph.events = copy.deepcopy(events)
		graph.relations = copy.deepcopy(relations)
		graph.marking = copy.deepcopy(marking)
		graph.nestedgroups = copy.deepcopy(nested_groups)
		graph.nested_events = copy.deepcopy(nested_events)

		# Ensure parent references are maintained in copied nested events
		for parent, children in graph.nestedgroups.items():
			for child in children:
				child.parent = parent

		return graph

	# Property getters and setters
	@property
	def nested_events(self):
		return self.__nested_events

	@nested_events.setter
	def nested_events(self, nested_events):
		self.__nested_events = nested_events

	@property
	def nestedgroups(self):
		return self.__nestedgroups

	@nestedgroups.setter
	def nestedgroups(self, nestedgroups):
		self.__nestedgroups = nestedgroups

	@property
	def marking(self):
		return self.__marking

	@marking.setter
	def marking(self, marking):
		self.__marking = marking

	@property
	def relations(self) -> Set['DCRRelation']:
		return self.__relations

	@relations.setter
	def relations(self, relations):
		self.__relations = relations

	@property
	def events(self) -> Set['Event']:
		return self.__events

	@events.setter
	def events(self, events):
		self.__events = events

	def get_event(self, activity: str) -> Optional[Event]:
		"""
		Helper function to get an event by its activity name.

		Args:
			activity: The name of the activity to find

		Returns:
			The Event object if found, None otherwise
		"""
		for event in self.events:
			if event.activity == activity:
				return event
		return None

	def add_relation(self, start_event: str | Event, target_event: str | Event,
					 relation_type: RelationTyps) -> None:
		"""
		Add a relation between two events. If the relation already exists, nothing happens.

		Args:
			start_event: The source event or its activity name
			target_event: The target event or its activity name
			type: The type of relation to add

		Raises:
			TypeError: If the event arguments are of invalid types
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
		if e is None:
			self.__relations.add(DCRRelation(start_event,target_event,relation_type))
    
	def get_relation(self, start_event: Event, target_event: Event, type: RelationTyps) -> DCRRelation | None:
		"""
		Return a specific edge between two events in the DCR graph.

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

		for r in self.relations:
			if matches(r):
				return r

		return None
			
	def remove_relation(self, relation: DCRRelation) -> bool:
		"""
		  Remove a relation from the graph.

		  Args:
			  relation: The relation to remove

		  Returns:
			  bool: True if relation was found and removed, False otherwise
		  """

		# Validate relation exists
		if relation not in self.relations:
			return False

		self.relations.discard(relation)
		return True

	def add_event(self, activity: str | Event, marking: Set[MarkingTyps] = {MarkingTyps.I},
				  isGroup: bool = False, parent: str = None) -> Event:
		"""
		Add a new event to the graph.

		Args:
			activity: The name of the event or the event
			marking: The initial marking of the event as set, empty set if event is neither executed, pending nor included (default: {Included})
			isGroup: Whether this is a group event (default: False)
			parent: Optional parent if event is part of a group

		Returns:
			The newly created or added Event object
		"""
		if isinstance(activity, str):
			# Create new event with given name and group status
			new_event = Event(activity, isGroup)
			# Handle parent group if specified
			if parent is not None:
				# Try to get existing parent event
				parent_event = self.get_event(parent)
				# If parent doesn't exist, create it as a group
				if parent_event is None:
					parent_event = self.add_event(parent, isGroup=True)
				new_event.parent = parent_event
		else:
			new_event = activity

		if new_event.isGroup:
			# initialize children set
			self.nestedgroups[new_event] = set()

		if new_event.parent is not None:
			# update parent's group status and children
			new_event.parent.isGroup = True
			self.nestedgroups.setdefault(new_event.parent, set()).add(new_event)

		self.events.add(new_event)
		for mark in marking:
			self.marking.add_event(new_event, mark)
		return new_event

	def add_nested_group(self, parent: str | Event, children: Set[str | Event]) -> None:
		"""
		Add a nested group.

		Args:
			parent: The parent event or its activity name
			children: Set of child events or their activity names

		Raises:
			TypeError: If the parent or children are of invalid types
		"""

		if isinstance(parent, str):
			# get parent event object
			parentEvent = self.get_event(parent)
			if parentEvent is None:
				# If parent doesn't exist, create it as a group
				parent = self.add_event(parent, isGroup=True)
			else:
				parent = parentEvent
		elif not isinstance(parent, Event):
			raise TypeError("parent must be either str or Event")

		parent.isGroup = True
		# Process each child in the set
		for child in children:
			if isinstance(child, str):
				# get child event
				child = self.get_event(child)
			elif not isinstance(child, Event):
				raise TypeError("child must be either str or Event")
			child.parent = parent
			# Initialize parent's child set if it doesn't exist
			if parent not in self.nestedgroups:
				self.nestedgroups[parent] = set()
			self.nestedgroups[parent].add(child)

	def get_incidental_relations(self, event: Event) -> Set[DCRRelation]:
		"""
		Get all relations connected to a specific event.

		Args:
			event: The event to find relations for

		Returns:
			Set of relations connected to the event and empty set if not in graph
		"""
		if self.get_event(event.activity) is None:
			return set()

		rel_set = set()
		for rel in self.relations:
			if rel.start_event == event or rel.target_event == event:
				rel_set.add(rel)
		return rel_set

	def _remove_incidental_relations(self, event: Event) -> None:
		"""Remove all relations connected to a specific event."""
		for rel in self.get_incidental_relations(event):
			self.relations.remove(rel)

	def remove_event(self, event: Event) -> None:
		"""
		Remove an event and all its connected relations.

		Args:
			event: The event to remove
		"""
		self._remove_incidental_relations(event)
		self.events.remove(event)
		self.marking.remove_event(event)

		if event.parent is not None:
			self.nestedgroups[event.parent].remove(event)

	def export_as_xml(self, output_file_name, dcr_title='DCR graph from ocpa') -> None:
		"""Exports the graph to xml file."""
		from ocpa.objects.oc_dcr_graph import export_dcr_xml
		export_dcr_xml(self, output_file_name=output_file_name, dcr_title=dcr_title)

	def __str__(self) -> str:
		"""Return a string representation of the graph."""
		from ocpa.util.dcr.converter import DCRConverter
		return str(DCRConverter.to_string_representation(self))