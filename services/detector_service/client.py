from __future__ import annotations
from typing import List, Tuple, Dict, Type
from abc import ABC, abstractmethod
import json
from collections import deque
import uuid
import os
import shutil
from datetime import datetime
import inspect
import time
import base64
from austin_heller_repo.socket_queued_message_framework import SourceTypeEnum, ClientServerMessage, ClientServerMessageTypeEnum, StructureStateEnum, StructureTransitionException, Structure, StructureFactory, StructureInfluence, ClientSocketFactory, ClientMessengerFactory
from austin_heller_repo.threading import Semaphore, start_thread
from austin_heller_repo.common import StringEnum, SubprocessWrapper, is_directory_empty

try:
	from .detector import DetectRequestDetectorClientServerMessage, DetectorClientServerMessage, DetectorClientServerMessageTypeEnum, DetectedLabel, DetectResponseDetectorClientServerMessage
except ImportError:
	from detector import DetectRequestDetectorClientServerMessage, DetectorClientServerMessage, DetectorClientServerMessageTypeEnum, DetectedLabel, DetectResponseDetectorClientServerMessage


class ClientSourceTypeEnum(SourceTypeEnum):
	Client = "client"
	Detector = "detector"


class ClientStructureStateEnum(StructureStateEnum):
	Active = "active"


class DetectorStructureStateEnum(StructureStateEnum):
	Active = "active"


class DetectorStructure(Structure):

	def __init__(self, *, source_uuid: str):
		super().__init__(
			states=DetectorStructureStateEnum,
			initial_state=DetectorStructureStateEnum.Active
		)

		self.__source_uuid = source_uuid

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		raise Exception(f"Unexpected connection from source {source_type.value}")

	def send_detection_request(self, *, image_bytes: bytes, image_extension: str, image_uuid: str):
		self.send_client_server_message(
			client_server_message=DetectRequestDetectorClientServerMessage(
				image_bytes_base64string=base64.b64encode(image_bytes).decode(),
				image_extension=image_extension,
				image_uuid=image_uuid,
				destination_uuid=self.__source_uuid
			)
		)


class ClientStructure(Structure):

	def __init__(self, *, detector_client_messenger_factory: ClientMessengerFactory):
		super().__init__(
			states=ClientStructureStateEnum,
			initial_state=ClientStructureStateEnum.Active
		)

		self.__detector_client_messenger_factory = detector_client_messenger_factory

		self.__detector_structure = None  # type: DetectorStructure
		self.__detector_structure_semaphore = Semaphore()
		self.__detected_labels_per_image_uuid = {}  # type: Dict[str, List[DetectedLabel]]
		self.__blocking_semaphore_per_image_uuid = {}  # type: Dict[str, Semaphore]

		self.add_transition(
			client_server_message_type=DetectorClientServerMessageTypeEnum.DetectResponse,
			from_source_type=ClientSourceTypeEnum.Detector,
			start_structure_state=ClientStructureStateEnum.Active,
			end_structure_state=ClientStructureStateEnum.Active,
			on_transition=self.__detector_detect_response_transition
		)

		self.__initialize()

	def __initialize(self):

		self.connect_to_outbound_messenger(
			client_messenger_factory=self.__detector_client_messenger_factory,
			source_type=ClientSourceTypeEnum.Detector,
			tag_json=None
		)

	def __detector_detect_response_transition(self, structure_influence: StructureInfluence):

		client_server_message = structure_influence.get_client_server_message()
		if not isinstance(client_server_message, DetectResponseDetectorClientServerMessage):
			raise Exception(f"Unexpected message type: {client_server_message.__class__.get_client_server_message_type()}")
		else:
			image_uuid = client_server_message.get_image_uuid()
			detected_labels = client_server_message.get_detected_labels()

			self.__detector_structure_semaphore.acquire()
			try:
				self.__detected_labels_per_image_uuid[image_uuid] = detected_labels
				self.__blocking_semaphore_per_image_uuid[image_uuid].release()
			finally:
				self.__detector_structure_semaphore.release()

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		if source_type == ClientSourceTypeEnum.Detector:
			self.__detector_structure = DetectorStructure(
				source_uuid=source_uuid
			)
			self.register_child_structure(
				structure=self.__detector_structure
			)
		else:
			raise Exception(f"Unexpected connection from source {source_type.value}")

	def get_detected_labels(self, *, image_file_path: str) -> List[DetectedLabel]:
		with open(image_file_path, "rb") as file_handle:
			image_bytes = file_handle.read()
		image_extension = os.path.splitext(image_file_path)[1]

		image_uuid = str(uuid.uuid4())

		blocking_semaphore = Semaphore()
		blocking_semaphore.acquire()

		self.__detector_structure_semaphore.acquire()
		try:
			self.__blocking_semaphore_per_image_uuid[image_uuid] = blocking_semaphore
		finally:
			self.__detector_structure_semaphore.release()

		self.__detector_structure.send_detection_request(
			image_bytes=image_bytes,
			image_extension=image_extension,
			image_uuid=image_uuid
		)

		blocking_semaphore.acquire()
		blocking_semaphore.release()

		self.__detector_structure_semaphore.acquire()
		try:
			detected_labels = self.__detected_labels_per_image_uuid[image_uuid]
			del self.__detected_labels_per_image_uuid[image_uuid]
			del self.__blocking_semaphore_per_image_uuid[image_uuid]
		finally:
			self.__detector_structure_semaphore.release()

		return detected_labels
