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
	from .trainer import AddImageAnnouncementTrainerClientServerMessage, ImageUsageTypeEnum, TrainerClientServerMessage, TrainerClientServerMessageTypeEnum
except ImportError:
	from trainer import AddImageAnnouncementTrainerClientServerMessage, ImageUsageTypeEnum, TrainerClientServerMessage, TrainerClientServerMessageTypeEnum


class ImageSourceSourceTypeEnum(SourceTypeEnum):
	ImageSource = "image_source"
	Trainer = "trainer"


class ImageSourceStructureStateEnum(StructureStateEnum):
	Active = "active"


class TrainerStructureStateEnum(StructureStateEnum):
	Active = "active"


class TrainerStructure(Structure):

	def __init__(self, *, source_uuid: str):
		super().__init__(
			states=TrainerStructureStateEnum,
			initial_state=TrainerStructureStateEnum.Active
		)

		self.__source_uuid = source_uuid

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		raise Exception(f"Unexpected connection from source {source_type.value}")

	def send_training_image(self, *, image_bytes: bytes, image_extension: str, annotation_bytes: bytes):
		self.send_client_server_message(
			client_server_message=AddImageAnnouncementTrainerClientServerMessage(
				image_bytes_base64string=base64.b64encode(image_bytes).decode(),
				image_extension=image_extension,
				annotation_bytes_base64string=base64.b64encode(annotation_bytes).decode(),
				image_usage_type_string=ImageUsageTypeEnum.Training.value,
				destination_uuid=self.__source_uuid
			)
		)

	def send_validation_image(self, *, image_bytes: bytes, image_extension: str, annotation_bytes: bytes):
		self.send_client_server_message(
			client_server_message=AddImageAnnouncementTrainerClientServerMessage(
				image_bytes_base64string=base64.b64encode(image_bytes).decode(),
				image_extension=image_extension,
				annotation_bytes_base64string=base64.b64encode(annotation_bytes).decode(),
				image_usage_type_string=ImageUsageTypeEnum.Validation.value,
				destination_uuid=self.__source_uuid
			)
		)


class ImageSourceStructure(Structure):

	def __init__(self, *, trainer_client_messenger_factory: ClientMessengerFactory):
		super().__init__(
			states=ImageSourceStructureStateEnum,
			initial_state=ImageSourceStructureStateEnum.Active
		)

		self.__trainer_client_messenger_factory = trainer_client_messenger_factory

		self.__trainer_structure = None  # type: TrainerStructure

		self.__initialize()

	def __initialize(self):

		self.connect_to_outbound_messenger(
			client_messenger_factory=self.__trainer_client_messenger_factory,
			source_type=ImageSourceSourceTypeEnum.Trainer,
			tag_json=None
		)

	def on_client_connected(self, *, source_uuid: str, source_type: SourceTypeEnum, tag_json: Dict or None):
		if source_type == ImageSourceSourceTypeEnum.Trainer:
			self.__trainer_structure = TrainerStructure(
				source_uuid=source_uuid
			)
			self.register_child_structure(
				structure=self.__trainer_structure
			)
		else:
			raise Exception(f"Unexpected connection from source {source_type.value}")

	def send_training_image(self, *, image_file_path: str, annotation_file_path: str):
		with open(image_file_path, "rb") as file_handle:
			image_bytes = file_handle.read()
		with open(annotation_file_path, "rb") as file_handle:
			annotation_bytes = file_handle.read()
		image_extension = os.path.splitext(image_file_path)[1]
		self.__trainer_structure.send_training_image(
			image_bytes=image_bytes,
			image_extension=image_extension,
			annotation_bytes=annotation_bytes
		)

	def send_validation_image(self, *, image_file_path: str, annotation_file_path: str):
		with open(image_file_path, "rb") as file_handle:
			image_bytes = file_handle.read()
		with open(annotation_file_path, "rb") as file_handle:
			annotation_bytes = file_handle.read()
		image_extension = os.path.splitext(image_file_path)[1]
		self.__trainer_structure.send_validation_image(
			image_bytes=image_bytes,
			image_extension=image_extension,
			annotation_bytes=annotation_bytes
		)
