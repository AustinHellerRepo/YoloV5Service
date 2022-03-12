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
from austin_heller_repo.socket_queued_message_framework import SourceTypeEnum, ClientServerMessage, ClientServerMessageTypeEnum, StructureStateEnum, StructureTransitionException, Structure, StructureFactory, StructureInfluence
from austin_heller_repo.threading import Semaphore, start_thread
from austin_heller_repo.common import StringEnum, SubprocessWrapper, is_directory_empty


class ImageUsageTypeEnum(StringEnum):
	Training = "training"
	Validation = "validation"
	Detect = "detect"


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


class ServiceSourceTypeEnum(SourceTypeEnum):
	Service = "service"
	Client = "client"


class ServiceStructureStateEnum(StructureStateEnum):
	Active = "active"


class ClientStructureStateEnum(StructureStateEnum):
	Active = "active"


class ServiceClientServerMessageTypeEnum(ClientServerMessageTypeEnum):
	# service
	ServiceError = "service_error"
	# client
	DetectRequest = "detect_request"
	DetectResponse = "detect_response"
	AddImageAnnouncement = "add_image_announcement"


class ServiceClientServerMessage(ClientServerMessage, ABC):

	def __init__(self, *, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		pass

	@classmethod
	def get_client_server_message_type_class(cls) -> Type[ClientServerMessageTypeEnum]:
		return ServiceClientServerMessageTypeEnum


###############################################################################
# Service
###############################################################################

class ServiceErrorServiceClientServerMessage(ServiceClientServerMessage):

	def __init__(self, *, structure_state_name: str, client_server_message_json_string: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__structure_state_name = structure_state_name
		self.__client_server_message_json_string = client_server_message_json_string

	def get_structure_state(self) -> ServiceStructureStateEnum:
		return ServiceStructureStateEnum(self.__structure_state_name)

	def get_client_server_message(self) -> ServiceClientServerMessage:
		return ServiceClientServerMessage.parse_from_json(
			json_object=json.loads(self.__client_server_message_json_string)
		)

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return ServiceClientServerMessageTypeEnum.ServiceError

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

class DetectRequestServiceClientServerMessage(ServiceClientServerMessage):

	def __init__(self, *, image_bytes: bytes, image_extension: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__image_bytes = image_bytes
		self.__image_extension = image_extension

	def get_image_bytes(self) -> bytes:
		return self.__image_bytes

	def get_image_extension(self) -> str:
		return self.__image_extension

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return ServiceClientServerMessageTypeEnum.DetectRequest

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["image_bytes"] = self.__image_bytes
		json_object["image_extension"] = self.__image_extension
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return ServiceErrorServiceClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


class DetectResponseServiceClientServerMessage(ServiceClientServerMessage):

	def __init__(self, *, detected_label_json_dicts: List[Dict], destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__detected_label_json_dicts = detected_label_json_dicts

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
		return ServiceClientServerMessageTypeEnum.DetectResponse

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["detected_label_json_dicts"] = self.__detected_label_json_dicts
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return ServiceErrorServiceClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


class AddImageAnnouncementServiceClientServerMessage(ServiceClientServerMessage):

	def __init__(self, *, image_bytes: bytes, image_extension: str, annotation_bytes: bytes, image_usage_type_string: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__image_bytes = image_bytes
		self.__image_extension = image_extension
		self.__annotation_bytes = annotation_bytes
		self.__image_usage_type_string = image_usage_type_string

	def get_image_bytes(self) -> bytes:
		return self.__image_bytes

	def get_image_extension(self) -> str:
		return self.__image_extension

	def get_annotation_bytes(self) -> bytes:
		return self.__annotation_bytes

	def get_image_usage_type(self) -> ImageUsageTypeEnum:
		return ImageUsageTypeEnum(self.__image_usage_type_string)

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return ServiceClientServerMessageTypeEnum.AddTrainingImageAnnouncement

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["image_bytes"] = self.__image_bytes
		json_object["image_extension"] = self.__image_extension
		json_object["annotation_bytes"] = self.__annotation_bytes
		json_object["image_usage_type_string"] = self.__image_usage_type_string
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return ServiceErrorServiceClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


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
			client_server_message=DetectResponseServiceClientServerMessage(
				detected_label_json_dicts=DetectedLabel.to_list_of_json(
					detected_labels=detected_labels
				),
				destination_uuid=self.__source_uuid
			)
		)


class ServiceStructure(Structure):

	def __init__(self, *, script_directory_path: str, temp_image_directory_path: str, training_directory_path: str, validation_directory_path: str, model_directory_path: str, image_size: int, training_batch_size: int, training_epochs: int):
		super().__init__(
			states=ServiceStructureStateEnum,
			initial_state=ServiceStructureStateEnum.Active
		)

		self.__script_directory_path = script_directory_path
		self.__temp_image_directory_path = temp_image_directory_path
		self.__training_directory_path = training_directory_path
		self.__validation_directory_path = validation_directory_path
		self.__model_directory_path = model_directory_path
		self.__image_size = image_size
		self.__training_batch_size = training_batch_size
		self.__training_epochs = training_epochs

		self.__training_script_file_path = None  # type: str
		self.__detection_script_file_path = None  # type: str
		self.__detection_model_semaphore = Semaphore()
		self.__detection_model_file_path = None  # type: str
		self.__training_model_file_path = None  # type: str
		self.__is_training_next_model_thread_active = True
		self.__training_subprocess_wrapper = None  # type: SubprocessWrapper
		self.__training_next_model_thread = None
		self.__available_image_uuids = []  # type: List[str]
		self.__available_image_uuids_semaphore = Semaphore()
		self.__directory_name_per_image_usage_type = {}  # type: Dict[ImageUsageTypeEnum, str]
		self.__client_structure_per_source_uuid = {}  # type: Dict[str, ClientStructure]

		self.add_transition(
			client_server_message_type=ServiceClientServerMessageTypeEnum.DetectRequest,
			from_source_type=ServiceSourceTypeEnum.Client,
			start_structure_state=ServiceStructureStateEnum.Active,
			end_structure_state=ServiceStructureStateEnum.Active,
			on_transition=self.__client_detect_request_transition
		)

		self.add_transition(
			client_server_message_type=ServiceClientServerMessageTypeEnum.AddImageAnnouncement,
			from_source_type=ServiceSourceTypeEnum.Client,
			start_structure_state=ServiceStructureStateEnum.Active,
			end_structure_state=ServiceStructureStateEnum.Active,
			on_transition=self.__client_add_image_announcement_transition
		)

		self.__initialize()

	def __initialize(self):

		self.__training_script_file_path = os.path.join(self.__script_directory_path, "train.sh")
		self.__detection_script_file_path = os.path.join(self.__script_directory_path, "detect.sh")

		self.__detection_model_file_path = os.path.join(self.__model_directory_path, "detection.pt")
		self.__training_model_file_path = os.path.join(self.__model_directory_path, "training.pt")

		self.__directory_name_per_image_usage_type[ImageUsageTypeEnum.Training] = "training"
		self.__directory_name_per_image_usage_type[ImageUsageTypeEnum.Validation] = "validation"
		self.__directory_name_per_image_usage_type[ImageUsageTypeEnum.Detect] = "detect"

		for image_usage_type in list(ImageUsageTypeEnum):
			if image_usage_type not in self.__directory_name_per_image_usage_type:
				raise Exception(f"Failed to define temp directory name for image usage type \"{image_usage_type.value}\".")

		self.__training_next_model_thread = start_thread(self.__training_next_model_thread_method)

	def __client_detect_request_transition(self, structure_influence: StructureInfluence):

		client_server_message = structure_influence.get_client_server_message()
		if not isinstance(client_server_message, DetectRequestServiceClientServerMessage):
			raise Exception(f"Unexpected message type: {client_server_message.__class__.get_client_server_message_type()}")
		else:
			image_bytes = client_server_message.get_image_bytes()
			image_extension = client_server_message.get_image_extension()
			if image_extension.startswith("."):
				image_extension = image_extension[1:]
			image_uuid = uuid.uuid4()
			image_file_path = os.path.join(self.__temp_image_directory_path, self.__directory_name_per_image_usage_type[ImageUsageTypeEnum.Detect], f"{image_uuid}.{image_extension}")
			try:
				with open(image_file_path, "wb") as file_handle:
					file_handle.write(image_bytes)

				# TODO start the detect process

			finally:
				if os.path.exists(image_file_path):
					os.unlink(image_file_path)

	def __client_add_image_announcement_transition(self, structure_influence: StructureInfluence):

		client_server_message = structure_influence.get_client_server_message()
		if not isinstance(client_server_message, AddImageAnnouncementServiceClientServerMessage):
			raise Exception(f"Unexpected message type: {client_server_message.__class__.get_client_server_message_type()}")
		else:
			image_bytes = client_server_message.get_image_bytes()
			image_extension = client_server_message.get_image_extension()
			if image_extension.startswith("."):
				image_extension = image_extension[1:]
			image_uuid = uuid.uuid4()
			image_usage_type_directory_name = self.__directory_name_per_image_usage_type[client_server_message.get_image_usage_type()]
			image_file_path = os.path.join(self.__temp_image_directory_path, image_usage_type_directory_name, f"{image_uuid}.{image_extension}")
			annotation_file_path = os.path.join(self.__temp_image_directory_path, image_usage_type_directory_name, f"{image_uuid}.txt")
			try:
				with open(image_file_path, "wb") as file_handle:
					file_handle.write(image_bytes)
				with open(annotation_file_path, "wb") as file_handle:
					file_handle.write(annotation_file_path)

				# make the image and annotation available to be brought over to the training environment for the model
				self.__available_image_uuids_semaphore.acquire()
				self.__available_image_uuids.append(image_uuid)
				self.__available_image_uuids_semaphore.release()
			finally:
				if os.path.exists(image_file_path):
					os.unlink(image_file_path)

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		if source_type == ServiceSourceTypeEnum.Client:
			client_structure = ClientStructure(
				source_uuid=source_uuid
			)
			self.__client_structure_per_source_uuid[source_uuid] = client_structure
		else:
			raise Exception(f"Unexpected connection from source: {source_type.value}")

	def __training_next_model_thread_method(self):

		try:
			while self.__is_training_next_model_thread_active:

				# check the available images and annotation for new training data
				self.__available_image_uuids_semaphore.acquire()
				if self.__available_image_uuids:
					for image_usage_type, destination_directory_path in [
						(ImageUsageTypeEnum.Training, self.__training_directory_path),
						(ImageUsageTypeEnum.Validation, self.__validation_directory_path)
					]:
						image_file_path_per_image_uuid = {}  # type: Dict[str, str]
						image_usage_type_directory_name = self.__directory_name_per_image_usage_type[image_usage_type]
						images_directory_path = os.path.join(self.__temp_image_directory_path, image_usage_type_directory_name)
						for file_name in os.listdir(images_directory_path):
							file_name_uuid = file_name.split(".")[0]  # type: str
							file_path = os.path.join(images_directory_path, file_name)
							image_file_path_per_image_uuid[file_name_uuid] = file_path

						for image_uuid in self.__available_image_uuids:
							if image_uuid in image_file_path_per_image_uuid:
								source_image_file_path = image_file_path_per_image_uuid[image_uuid]
								destination_image_file_path = os.path.join(destination_directory_path, "images", os.path.basename(source_image_file_path))
								shutil.move(source_image_file_path, destination_image_file_path)

								source_annotation_file_path = os.path.join(self.__temp_image_directory_path, f"{image_uuid}.txt")
								destination_annotation_file_path = os.path.join(destination_directory_path, "annotations", f"{image_uuid}.txt")
								shutil.move(source_annotation_file_path, destination_annotation_file_path)

					self.__available_image_uuids.clear()
				self.__available_image_uuids_semaphore.release()

				# run training process

				training_weights_file_name = ""
				if os.path.exists(os.path.join(self.__model_directory_path, "training.pt")):
					training_weights_file_name = "training.pt"
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Found existing training weights")
				else:
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Failed to find existing training weights")

				if is_directory_empty(os.path.join(self.__training_directory_path, "images")):
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Failed to find training images.")
					time.sleep(1.0)
				elif is_directory_empty(os.path.join(self.__validation_directory_path, "images")):
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Failed to find validation images.")
					time.sleep(1.0)
				else:
					self.__training_subprocess_wrapper = SubprocessWrapper(
						command="sh",
						arguments=[self.__training_script_file_path, str(self.__image_size), str(self.__training_batch_size), str(self.__training_epochs), training_weights_file_name]
					)
					training_output = self.__training_subprocess_wrapper.run()
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Training output: (start)\n{training_output}")
					print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: Training output: (end)")
					# TODO save output to log

					# TODO ensure that training weights are saved to appropriate file path

					self.__training_subprocess_wrapper = None

					self.__detection_model_semaphore.acquire()
					try:
						# replace detect model with trained model
						shutil.copy(self.__training_model_file_path, self.__detection_model_file_path)
					finally:
						self.__detection_model_semaphore.release()
		except Exception as ex:
			print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: ex: {ex}")
			raise

	def dispose(self):
		super().dispose()
		self.__is_training_next_model_thread_active = False
		if self.__training_subprocess_wrapper is not None:
			self.__training_subprocess_wrapper.kill()


class ServiceStructureFactory(StructureFactory):

	def get_structure(self) -> Structure:
		raise NotImplementedError()  # TODO
