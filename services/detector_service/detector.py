from __future__ import annotations
import sys

sys.path.append("..")

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
from austin_heller_repo.socket_queued_message_framework import SourceTypeEnum, ClientServerMessage, ClientServerMessageTypeEnum, StructureStateEnum, StructureTransitionException, Structure, StructureFactory, StructureInfluence, ClientMessengerFactory, ClientMessenger
from austin_heller_repo.threading import Semaphore, start_thread
from austin_heller_repo.common import StringEnum, SubprocessWrapper, is_directory_empty

try:
	from trainer_service.trainer import UpdateModelBroadcastTrainerClientServerMessage, TrainerClientServerMessageTypeEnum, TrainerClientServerMessage
except ImportError:
	from trainer import UpdateModelBroadcastTrainerClientServerMessage, TrainerClientServerMessageTypeEnum, TrainerClientServerMessage


class DetectedLabel():

	def __init__(self, *, label_index: int, x: int, y: int, width: int, height: int, confidence: float):

		self.__label_index = label_index
		self.__x = x
		self.__y = y
		self.__width = width
		self.__height = height
		self.__confidence = confidence

	def to_json(self) -> Dict:
		return {
			"label_index": self.__label_index,
			"x": self.__x,
			"y": self.__y,
			"width": self.__width,
			"height": self.__height,
			"confidence": self.__confidence
		}

	@staticmethod
	def parse_json(json_dict: Dict) -> DetectedLabel:
		return DetectedLabel(**json_dict)

	@staticmethod
	def to_list_of_json(detected_labels: List[DetectedLabel]) -> List[Dict]:
		detected_label_json_dicts = []  # type: List[Dict]
		for detected_label in detected_labels:
			detected_label_json_dict = detected_label.to_json()
			detected_label_json_dicts.append(detected_label_json_dict)
		return detected_label_json_dicts


class DetectorSourceTypeEnum(SourceTypeEnum):
	Detector = "detector"
	Trainer = "trainer"
	Client = "client"


class DetectorStructureStateEnum(StructureStateEnum):
	Active = "active"


class ClientStructureStateEnum(StructureStateEnum):
	Active = "active"


class DetectorClientServerMessageTypeEnum(ClientServerMessageTypeEnum):
	# detector
	DetectorError = "detector_error"
	# trainer
	# NOP
	# client
	DetectRequest = "detect_request"
	DetectResponse = "detect_response"


class DetectorClientServerMessage(ClientServerMessage, ABC):

	def __init__(self, *, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		pass

	@classmethod
	def get_client_server_message_type_class(cls) -> Type[ClientServerMessageTypeEnum]:
		return DetectorClientServerMessageTypeEnum


###############################################################################
# Detector
###############################################################################

class DetectorErrorDetectorClientServerMessage(DetectorClientServerMessage):

	def __init__(self, *, structure_state_name: str, client_server_message_json_string: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__structure_state_name = structure_state_name
		self.__client_server_message_json_string = client_server_message_json_string

	def get_structure_state(self) -> DetectorStructureStateEnum:
		return DetectorStructureStateEnum(self.__structure_state_name)

	def get_client_server_message(self) -> DetectorClientServerMessage:
		return DetectorClientServerMessage.parse_from_json(
			json_object=json.loads(self.__client_server_message_json_string)
		)

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return DetectorClientServerMessageTypeEnum.DetectorError

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["structure_state_name"] = self.__structure_state_name
		json_object["client_server_message_json_string"] = self.__client_server_message_json_string
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return None


###############################################################################
# Client
###############################################################################

class DetectRequestDetectorClientServerMessage(DetectorClientServerMessage):

	def __init__(self, *, image_bytes_base64string: str, image_extension: str, image_uuid: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__image_bytes_base64string = image_bytes_base64string
		self.__image_extension = image_extension
		self.__image_uuid = image_uuid

	def get_image_bytes(self) -> bytes:
		return base64.b64decode(self.__image_bytes_base64string.encode())

	def get_image_extension(self) -> str:
		return self.__image_extension

	def get_image_uuid(self) -> str:
		return self.__image_uuid

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return DetectorClientServerMessageTypeEnum.DetectRequest

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["image_bytes_base64string"] = self.__image_bytes_base64string
		json_object["image_extension"] = self.__image_extension
		json_object["image_uuid"] = self.__image_uuid
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return DetectorErrorDetectorClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


class DetectResponseDetectorClientServerMessage(DetectorClientServerMessage):

	def __init__(self, *, image_uuid: str, detected_label_json_dicts: List[Dict], destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__image_uuid = image_uuid
		self.__detected_label_json_dicts = detected_label_json_dicts

	def get_image_uuid(self) -> str:
		return self.__image_uuid

	def get_detected_labels(self) -> List[DetectedLabel]:
		detected_labels = []  # type: List[DetectedLabel]
		for detected_label_json_dict in self.__detected_label_json_dicts:
			detected_label = DetectedLabel.parse_json(
				json_dict=detected_label_json_dict
			)
			detected_labels.append(detected_label)
		return detected_labels

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return DetectorClientServerMessageTypeEnum.DetectResponse

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["image_uuid"] = self.__image_uuid
		json_object["detected_label_json_dicts"] = self.__detected_label_json_dicts
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return DetectorErrorDetectorClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


###############################################################################
# Structures
###############################################################################

class ClientStructure(Structure):

	def __init__(self, *, source_uuid: str):
		super().__init__(
			states=ClientStructureStateEnum,
			initial_state=ClientStructureStateEnum.Active
		)

		self.__source_uuid = source_uuid

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		raise Exception(f"Client connection not expected.")

	def send_detection_response(self, *, detected_labels: List[DetectedLabel]):
		self.send_client_server_message(
			client_server_message=DetectResponseDetectorClientServerMessage(
				detected_label_json_dicts=DetectedLabel.to_list_of_json(
					detected_labels=detected_labels
				),
				destination_uuid=self.__source_uuid
			)
		)


class DetectorStructure(Structure):

	def __init__(self, *, script_directory_path: str, temp_image_directory_path: str, model_directory_path: str, trainer_client_messenger_factory: ClientMessengerFactory, image_size: int, is_debug: bool = False):
		super().__init__(
			states=DetectorStructureStateEnum,
			initial_state=DetectorStructureStateEnum.Active
		)

		self.__script_directory_path = script_directory_path
		self.__temp_image_directory_path = temp_image_directory_path
		self.__model_directory_path = model_directory_path
		self.__trainer_client_messenger_factory = trainer_client_messenger_factory
		self.__image_size = image_size
		self.__is_debug = is_debug

		self.__detection_script_file_path = None  # type: str
		self.__detection_model_semaphore = Semaphore()
		self.__detection_model_file_path = None  # type: str
		self.__detection_subprocess_wrapper = None  # type: SubprocessWrapper
		self.__client_structure_per_source_uuid = {}  # type: Dict[str, ClientStructure]

		self.add_transition(
			client_server_message_type=DetectorClientServerMessageTypeEnum.DetectRequest,
			from_source_type=DetectorSourceTypeEnum.Client,
			start_structure_state=DetectorStructureStateEnum.Active,
			end_structure_state=DetectorStructureStateEnum.Active,
			on_transition=self.__client_detect_request_transition
		)

		self.add_transition(
			client_server_message_type=TrainerClientServerMessageTypeEnum.UpdateModelBroadcast,
			from_source_type=DetectorSourceTypeEnum.Trainer,
			start_structure_state=DetectorStructureStateEnum.Active,
			end_structure_state=DetectorStructureStateEnum.Active,
			on_transition=self.__trainer_update_model_broadcast_transition
		)

		self.__initialize()

	def __initialize(self):

		self.__detection_script_file_path = os.path.join(self.__script_directory_path, "detect.sh")

		self.__detection_model_file_path = os.path.join(self.__model_directory_path, "weights.pt")

		self.connect_to_outbound_messenger(
			client_messenger_factory=self.__trainer_client_messenger_factory,
			source_type=DetectorSourceTypeEnum.Trainer,
			tag_json=None
		)

	def __client_detect_request_transition(self, structure_influence: StructureInfluence):

		client_server_message = structure_influence.get_client_server_message()
		if not isinstance(client_server_message, DetectRequestDetectorClientServerMessage):
			raise Exception(f"Unexpected message type: {client_server_message.__class__.get_client_server_message_type()}")
		else:
			# run detection process

			if not os.path.exists(self.__detection_model_file_path):
				if self.__is_debug:
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Failed to find existing weights")
			else:
				if self.__is_debug:
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Found existing training weights")

				image_bytes = client_server_message.get_image_bytes()
				image_extension = client_server_message.get_image_extension()

				if image_extension.startswith("."):
					image_extension = image_extension[1:]

				image_file_path = os.path.join(self.__temp_image_directory_path, f"{uuid.uuid4()}.{image_extension}")
				with open(image_file_path, "wb") as file_handle:
					file_handle.write(image_bytes)

				self.__detection_model_semaphore.acquire()
				try:
					self.__detection_subprocess_wrapper = SubprocessWrapper(
						command="sh",
						arguments=[self.__detection_script_file_path, image_file_path, self.__detection_model_file_path, str(self.__image_size)]
					)
					if self.__is_debug:
						print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Detection shell script: (start)")
					exit_code, detection_output = self.__detection_subprocess_wrapper.run()
					if self.__is_debug:
						print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Detection exit code: {exit_code}")
						print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Detection output: {detection_output}")
						print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Detection shell script: (end)")

					detection_directory_path = None
					for line in detection_output.split("\n"):
						if line.startswith("Results saved to"):
							if self.__is_debug:
								print(line.encode())
							detection_directory_path = os.path.join("/app/yolov5", line[31:-4])
							break

					if detection_directory_path is None:
						if self.__is_debug:
							print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: failed to find detection directory path")
					else:
						# TODO send detection response for image_uuid
						if self.__is_debug:
							print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: found detection directory path: {detection_directory_path}")
							exists = os.path.exists(detection_directory_path)
							print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: exists: {exists}")
							is_directory = os.path.isdir(detection_directory_path)
							print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: is_directory: {is_directory}")
							is_file = os.path.isfile(detection_directory_path)
							print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: is_file: {is_file}")
							for file_name in os.listdir(detection_directory_path):
								file_path = os.path.join(detection_directory_path, file_name)
								print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: found file: {file_path}")
						label_directory_path = os.path.join(detection_directory_path, "labels")
						if not os.path.exists(label_directory_path):
							if self.__is_debug:
								print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: failed to find label directory path: {label_directory_path}")
						else:
							if self.__is_debug:
								print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: found label directory path: {label_directory_path}")
								for file_name in os.listdir(label_directory_path):
									file_path = os.path.join(label_directory_path, file_name)
									print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: found file: {file_path}")

						pass

					self.__detection_subprocess_wrapper = None

				finally:
					self.__detection_model_semaphore.release()

	def __trainer_update_model_broadcast_transition(self, structure_influence: StructureInfluence):

		client_server_message = structure_influence.get_client_server_message()
		if not isinstance(client_server_message, UpdateModelBroadcastTrainerClientServerMessage):
			raise Exception(f"Unexpected message type: {client_server_message.__class__.get_client_server_message_type()}")
		else:
			if self.__is_debug:
				print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: updating model from trainer")
			model_bytes = client_server_message.get_model_bytes()
			self.__detection_model_semaphore.acquire()
			try:
				with open(self.__detection_model_file_path, "wb") as file_handle:
					file_handle.write(model_bytes)
			finally:
				self.__detection_model_semaphore.release()
			if self.__is_debug:
				print(f"{datetime.utcnow()}: DetectorStructure: {inspect.stack()[0][3]}: updated model from trainer")

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		if source_type == DetectorSourceTypeEnum.Client:
			client_structure = ClientStructure(
				source_uuid=source_uuid
			)
			self.__client_structure_per_source_uuid[source_uuid] = client_structure
		elif source_type == DetectorSourceTypeEnum.Trainer:
			if self.__is_debug:
				print(f"Connected to trainer.")
		else:
			raise Exception(f"Unexpected connection from source: {source_type.value}")

	def dispose(self):
		super().dispose()
		if self.__detection_subprocess_wrapper is not None:
			self.__detection_subprocess_wrapper.kill()


class DetectorStructureFactory(StructureFactory):

	def __init__(self, *, script_directory_path: str, temp_image_directory_path: str, model_directory_path: str, trainer_client_messenger_factory: ClientMessengerFactory, image_size: int, is_debug: bool = False):

		self.__script_directory_path = script_directory_path
		self.__temp_image_directory_path = temp_image_directory_path
		self.__model_directory_path = model_directory_path
		self.__trainer_client_messenger_factory = trainer_client_messenger_factory
		self.__image_size = image_size
		self.__is_debug = is_debug

	def get_structure(self) -> Structure:
		return DetectorStructure(
			script_directory_path=self.__script_directory_path,
			temp_image_directory_path=self.__temp_image_directory_path,
			model_directory_path=self.__model_directory_path,
			trainer_client_messenger_factory=self.__trainer_client_messenger_factory,
			image_size=self.__image_size,
			is_debug=self.__is_debug
		)
