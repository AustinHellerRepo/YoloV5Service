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
from austin_heller_repo.socket_queued_message_framework import SourceTypeEnum, ClientServerMessage, ClientServerMessageTypeEnum, StructureStateEnum, StructureTransitionException, Structure, StructureFactory, StructureInfluence, ReadWriteSocketClosedException
from austin_heller_repo.threading import Semaphore, start_thread
from austin_heller_repo.common import StringEnum, SubprocessWrapper, is_directory_empty


class ImageUsageTypeEnum(StringEnum):
	Training = "training"
	Validation = "validation"


class TrainerSourceTypeEnum(SourceTypeEnum):
	Trainer = "trainer_service"
	ImageSource = "image_source"
	Detector = "detector_service"


class TrainerStructureStateEnum(StructureStateEnum):
	Active = "active"


class DetectorStructureStateEnum(StructureStateEnum):
	Active = "active"


class TrainerClientServerMessageTypeEnum(ClientServerMessageTypeEnum):
	# trainer_service
	TrainerError = "service_error"
	# client
	AddImageAnnouncement = "add_image_announcement"
	# detector
	UpdateModelBroadcast = "update_model_broadcast"


class TrainerClientServerMessage(ClientServerMessage, ABC):

	def __init__(self, *, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		pass

	@classmethod
	def get_client_server_message_type_class(cls) -> Type[ClientServerMessageTypeEnum]:
		return TrainerClientServerMessageTypeEnum


###############################################################################
# Trainer
###############################################################################

class TrainerErrorTrainerClientServerMessage(TrainerClientServerMessage):

	def __init__(self, *, structure_state_name: str, client_server_message_json_string: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__structure_state_name = structure_state_name
		self.__client_server_message_json_string = client_server_message_json_string

	def get_structure_state(self) -> TrainerStructureStateEnum:
		return TrainerStructureStateEnum(self.__structure_state_name)

	def get_client_server_message(self) -> TrainerClientServerMessage:
		return TrainerClientServerMessage.parse_from_json(
			json_object=json.loads(self.__client_server_message_json_string)
		)

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return TrainerClientServerMessageTypeEnum.TrainerError

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

class AddImageAnnouncementTrainerClientServerMessage(TrainerClientServerMessage):

	def __init__(self, *, image_bytes_base64string: str, image_extension: str, annotation_bytes_base64string: str, image_usage_type_string: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__image_bytes_base64string = image_bytes_base64string
		self.__image_extension = image_extension
		self.__annotation_bytes_base64string = annotation_bytes_base64string
		self.__image_usage_type_string = image_usage_type_string

	def get_image_bytes(self) -> bytes:
		return base64.b64decode(self.__image_bytes_base64string.encode())

	def get_image_extension(self) -> str:
		return self.__image_extension

	def get_annotation_bytes(self) -> bytes:
		return base64.b64decode(self.__annotation_bytes_base64string.encode())

	def get_image_usage_type(self) -> ImageUsageTypeEnum:
		return ImageUsageTypeEnum(self.__image_usage_type_string)

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return TrainerClientServerMessageTypeEnum.AddImageAnnouncement

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["image_bytes_base64string"] = self.__image_bytes_base64string
		json_object["image_extension"] = self.__image_extension
		json_object["annotation_bytes_base64string"] = self.__annotation_bytes_base64string
		json_object["image_usage_type_string"] = self.__image_usage_type_string
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return TrainerErrorTrainerClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


###############################################################################
# Detector
###############################################################################

class UpdateModelBroadcastTrainerClientServerMessage(TrainerClientServerMessage):

	def __init__(self, *, model_bytes_base64string: str, destination_uuid: str):
		super().__init__(
			destination_uuid=destination_uuid
		)

		self.__model_bytes_base64string = model_bytes_base64string

	def get_model_bytes(self) -> bytes:
		return base64.b64decode(self.__model_bytes_base64string.encode())

	@classmethod
	def get_client_server_message_type(cls) -> ClientServerMessageTypeEnum:
		return TrainerClientServerMessageTypeEnum.UpdateModelBroadcast

	def to_json(self) -> Dict:
		json_object = super().to_json()
		json_object["model_bytes_base64string"] = self.__model_bytes_base64string
		return json_object

	def get_structural_error_client_server_message_response(self, *, structure_transition_exception: StructureTransitionException, destination_uuid: str) -> ClientServerMessage:
		return TrainerErrorTrainerClientServerMessage(
			structure_state_name=structure_transition_exception.get_structure_state().value,
			client_server_message_json_string=json.dumps(structure_transition_exception.get_structure_influence().get_client_server_message().to_json()),
			destination_uuid=destination_uuid
		)


###############################################################################
# Structures
###############################################################################

class DetectorStructure(Structure):

	def __init__(self, *, source_uuid: str):
		super().__init__(
			states=DetectorStructureStateEnum,
			initial_state=DetectorStructureStateEnum.Active
		)

		self.__source_uuid = source_uuid

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		raise Exception(f"Unexpected connection from source {source_type.value}")

	def send_updated_model(self, *, model_bytes: bytes):
		self.send_client_server_message(
			client_server_message=UpdateModelBroadcastTrainerClientServerMessage(
				model_bytes_base64string=base64.b64encode(model_bytes).decode(),
				destination_uuid=self.__source_uuid
			)
		)


class TrainerStructure(Structure):

	def __init__(self, *, script_directory_path: str, temp_image_directory_path: str, training_directory_path: str, validation_directory_path: str, model_directory_path: str, yolov5_directory_path: str, image_size: int, training_batch_size: int, training_epochs: int, is_debug: bool = False):
		super().__init__(
			states=TrainerStructureStateEnum,
			initial_state=TrainerStructureStateEnum.Active
		)

		self.__script_directory_path = script_directory_path
		self.__temp_image_directory_path = temp_image_directory_path
		self.__training_directory_path = training_directory_path
		self.__validation_directory_path = validation_directory_path
		self.__model_directory_path = model_directory_path
		self.__yolov5_directory_path = yolov5_directory_path
		self.__image_size = image_size
		self.__training_batch_size = training_batch_size
		self.__training_epochs = training_epochs
		self.__is_debug = is_debug

		self.__training_script_file_path = None  # type: str
		self.__training_model_file_path = None  # type: str
		self.__training_model_file_path_semaphore = Semaphore()
		self.__is_training_model_thread_active = True
		self.__training_subprocess_wrapper = None  # type: SubprocessWrapper
		self.__training_model_thread = None
		self.__available_image_uuids = []  # type: List[str]
		self.__available_image_uuids_semaphore = Semaphore()
		self.__directory_name_per_image_usage_type = {}  # type: Dict[ImageUsageTypeEnum, str]
		self.__detector_structure_per_source_uuid = {}  # type: Dict[str, DetectorStructure]
		self.__detector_structure_per_source_uuid_semaphore = Semaphore()

		self.add_transition(
			client_server_message_type=TrainerClientServerMessageTypeEnum.AddImageAnnouncement,
			from_source_type=TrainerSourceTypeEnum.ImageSource,
			start_structure_state=TrainerStructureStateEnum.Active,
			end_structure_state=TrainerStructureStateEnum.Active,
			on_transition=self.__image_source_add_image_announcement_transition
		)

		self.__initialize()

	def __initialize(self):

		self.__training_script_file_path = os.path.join(self.__script_directory_path, "train.sh")
		self.__training_model_file_path = os.path.join(self.__model_directory_path, "training.pt")

		self.__directory_name_per_image_usage_type[ImageUsageTypeEnum.Training] = "training"
		self.__directory_name_per_image_usage_type[ImageUsageTypeEnum.Validation] = "validation"

		for image_usage_type in list(ImageUsageTypeEnum):
			if image_usage_type not in self.__directory_name_per_image_usage_type:
				raise Exception(f"Failed to define temp directory name for image usage type \"{image_usage_type.value}\".")

		self.__training_model_thread = start_thread(self.__training_model_thread_method)

	def __image_source_add_image_announcement_transition(self, structure_influence: StructureInfluence):

		client_server_message = structure_influence.get_client_server_message()
		if not isinstance(client_server_message, AddImageAnnouncementTrainerClientServerMessage):
			raise Exception(f"Unexpected message type: {client_server_message.__class__.get_client_server_message_type()}")
		else:
			image_bytes = client_server_message.get_image_bytes()
			image_extension = client_server_message.get_image_extension()
			if image_extension.startswith("."):
				image_extension = image_extension[1:]
			annotation_bytes = client_server_message.get_annotation_bytes()

			image_uuid = str(uuid.uuid4())
			image_usage_type_directory_name = self.__directory_name_per_image_usage_type[client_server_message.get_image_usage_type()]
			image_file_path = os.path.join(self.__temp_image_directory_path, image_usage_type_directory_name, f"{image_uuid}.{image_extension}")
			annotation_file_path = os.path.join(self.__temp_image_directory_path, image_usage_type_directory_name, f"{image_uuid}.txt")

			if self.__is_debug:
				print(f"{datetime.utcnow()}: TrainerStructure: __image_source_add_image_announcement_transition: saving image to {image_file_path}")
			with open(image_file_path, "wb") as file_handle:
				file_handle.write(image_bytes)

			if self.__is_debug:
				print(f"{datetime.utcnow()}: TrainerStructure: __image_source_add_image_announcement_transition: saving annotation to {annotation_file_path}")
			with open(annotation_file_path, "wb") as file_handle:
				file_handle.write(annotation_bytes)

			# make the image and annotation available to be brought over to the training environment for the model
			self.__available_image_uuids_semaphore.acquire()
			self.__available_image_uuids.append(image_uuid)
			self.__available_image_uuids_semaphore.release()

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		if source_type == TrainerSourceTypeEnum.ImageSource:
			# image source structure not needed at the moment
			print(f"{datetime.utcnow()}: TrainerStructure: on_client_connected: Image source connected.")
			pass
		elif source_type == TrainerSourceTypeEnum.Detector:
			detector_structure = DetectorStructure(
				source_uuid=source_uuid
			)
			self.register_child_structure(
				structure=detector_structure
			)
			self.__detector_structure_per_source_uuid_semaphore.acquire()
			try:
				self.__training_model_file_path_semaphore.acquire()
				try:
					with open(self.__training_model_file_path, "rb") as file_handle:
						model_bytes = file_handle.read()
					detector_structure.send_updated_model(
						model_bytes=model_bytes
					)
					self.__detector_structure_per_source_uuid[source_uuid] = detector_structure
				finally:
					self.__training_model_file_path_semaphore.release()
			finally:
				self.__detector_structure_per_source_uuid_semaphore.release()
		else:
			raise Exception(f"Unexpected connection from source: {source_type.value}")

	def __training_model_thread_method(self):

		try:
			while self.__is_training_model_thread_active:

				# check the available images and annotation for new training data
				self.__available_image_uuids_semaphore.acquire()
				if self.__available_image_uuids:
					for image_usage_type, destination_directory_path in [
						(ImageUsageTypeEnum.Training, self.__training_directory_path),
						(ImageUsageTypeEnum.Validation, self.__validation_directory_path)
					]:
						image_file_path_per_image_uuid = {}  # type: Dict[str, str]
						annotation_file_path_per_image_uuid = {}  # type: Dict[str, str]
						image_usage_type_directory_name = self.__directory_name_per_image_usage_type[image_usage_type]
						images_directory_path = os.path.join(self.__temp_image_directory_path, image_usage_type_directory_name)
						for file_name in os.listdir(images_directory_path):
							file_name_uuid = file_name.split(".")[0]  # type: str
							file_path = os.path.join(images_directory_path, file_name)
							if not file_name.endswith(".txt"):
								image_file_path_per_image_uuid[file_name_uuid] = file_path
							else:
								annotation_file_path_per_image_uuid[file_name_uuid] = file_path

						for image_uuid in self.__available_image_uuids:
							if image_uuid in image_file_path_per_image_uuid:
								source_image_file_path = image_file_path_per_image_uuid[image_uuid]
								destination_image_file_path = os.path.join(destination_directory_path, "images", os.path.basename(source_image_file_path))
								if self.__is_debug:
									print(f"{datetime.utcnow()}: TrainerStructure: __training_model_thread_method: moving image from {source_image_file_path} to {destination_image_file_path}")
								shutil.move(source_image_file_path, destination_image_file_path)

								source_annotation_file_path = annotation_file_path_per_image_uuid[image_uuid]
								destination_annotation_file_path = os.path.join(destination_directory_path, "labels", os.path.basename(source_annotation_file_path))
								if self.__is_debug:
									print(f"{datetime.utcnow()}: TrainerStructure: __training_model_thread_method: moving annotation from {source_annotation_file_path} to {destination_annotation_file_path}")
								shutil.move(source_annotation_file_path, destination_annotation_file_path)

					self.__available_image_uuids.clear()
				self.__available_image_uuids_semaphore.release()

				# run training process

				if os.path.exists(self.__training_model_file_path):
					training_weights_file_path = self.__training_model_file_path
					if self.__is_debug:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Found existing training weights")
				else:
					training_weights_file_path = ""
					if self.__is_debug:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Failed to find existing training weights")

				training_images_directory_path = os.path.join(self.__training_directory_path, "images")
				validation_images_directory_path = os.path.join(self.__validation_directory_path, "images")
				if is_directory_empty(training_images_directory_path):
					if self.__is_debug:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Failed to find training images at directory {training_images_directory_path}.")
				elif is_directory_empty(validation_images_directory_path):
					if self.__is_debug:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Failed to find validation images at directory {validation_images_directory_path}.")
				else:
					training_python_file_path = os.path.join(self.__yolov5_directory_path, "train.py")
					self.__training_subprocess_wrapper = SubprocessWrapper(
						command="sh",
						arguments=[self.__training_script_file_path, training_python_file_path, str(self.__image_size), str(self.__training_batch_size), str(self.__training_epochs), training_weights_file_path]
					)
					if self.__is_debug:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Training shell script: (start)")
					exit_code, training_output = self.__training_subprocess_wrapper.run()
					if self.__is_debug:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Training exit code: {exit_code}")
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Training output: {training_output}")
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: Training shell script: (end)")
					# TODO save output to log

					# ensure that training weights are saved to appropriate file path
					destination_last_model_file_path = None
					for line in training_output.split("\n"):
						path_index = None
						if line.startswith("Optimizer stripped from ../yolov5/runs/train/exp") and "last.pt" in line:
							path_index = 34
						elif line.startswith("Optimizer stripped from yolov5/runs/train/exp") and "last.pt" in line:
							path_index = 31

						if path_index is not None:
							source_last_model_file_path = os.path.join(self.__yolov5_directory_path, line[path_index:line.index("last.pt")], "last.pt")
							destination_last_model_file_path = os.path.join(self.__model_directory_path, "training.pt")
							if self.__is_debug:
								print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: saving model from {source_last_model_file_path} to {destination_last_model_file_path}")
							shutil.copy(source_last_model_file_path, destination_last_model_file_path)
							break

					self.__training_subprocess_wrapper = None

					if destination_last_model_file_path is None:
						print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: failed to find latest model.")
					else:
						# get trained weights file path to send to detectors

						if self.__is_debug:
							print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: broadcasting updated model to detectors.")

						self.__detector_structure_per_source_uuid_semaphore.acquire()
						try:
							with open(destination_last_model_file_path, "rb") as file_handle:
								model_bytes = file_handle.read()

							disconnected_detector_source_uuids = []  # type: List[str]
							for source_uuid, detector_structure in self.__detector_structure_per_source_uuid.items():
								try:
									detector_structure.send_updated_model(
										model_bytes=model_bytes
									)
									if self.__is_debug:
										print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: broadcasted updated model to detector {source_uuid}.")
								except ReadWriteSocketClosedException as ex:
									if self.__is_debug:
										print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: disconnected from detector {source_uuid}.")
									disconnected_detector_source_uuids.append(source_uuid)
								except Exception as ex:
									print(f"{datetime.utcnow()}: TrainerStructure: {inspect.stack()[0][3]}: ex: {ex}")

							for source_uuid in disconnected_detector_source_uuids:
								del self.__detector_structure_per_source_uuid[source_uuid]

						finally:
							self.__detector_structure_per_source_uuid_semaphore.release()

				time.sleep(10.0)

		except Exception as ex:
			print(f"{datetime.utcnow()}: {inspect.stack()[0][3]}: ex: {ex}")
			raise

	def dispose(self):
		super().dispose()
		self.__is_training_model_thread_active = False
		if self.__training_subprocess_wrapper is not None:
			self.__training_subprocess_wrapper.kill()


class TrainerStructureFactory(StructureFactory):

	def __init__(self, *, script_directory_path: str, temp_image_directory_path: str, training_directory_path: str, validation_directory_path: str, model_directory_path: str, yolov5_directory_path: str, image_size: int, training_batch_size: int, training_epochs: int, is_debug: bool = False):

		self.__script_directory_path = script_directory_path
		self.__temp_image_directory_path = temp_image_directory_path
		self.__training_directory_path = training_directory_path
		self.__validation_directory_path = validation_directory_path
		self.__model_directory_path = model_directory_path
		self.__yolov5_directory_path = yolov5_directory_path
		self.__image_size = image_size
		self.__training_batch_size = training_batch_size
		self.__training_epochs = training_epochs
		self.__is_debug = is_debug

	def get_structure(self) -> Structure:
		return TrainerStructure(
			script_directory_path=self.__script_directory_path,
			temp_image_directory_path=self.__temp_image_directory_path,
			training_directory_path=self.__training_directory_path,
			validation_directory_path=self.__validation_directory_path,
			model_directory_path=self.__model_directory_path,
			yolov5_directory_path=self.__yolov5_directory_path,
			image_size=self.__image_size,
			training_batch_size=self.__training_batch_size,
			training_epochs=self.__training_epochs,
			is_debug=self.__is_debug
		)
