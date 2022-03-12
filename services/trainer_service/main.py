from __future__ import annotations
import os
import sys
import time
from austin_heller_repo.socket_queued_message_framework import ServerMessenger, ServerSocketFactory, HostPointer

try:
	from .trainer import TrainerStructureFactory, TrainerSourceTypeEnum, TrainerClientServerMessage, TrainerClientServerMessageTypeEnum
except ImportError:
	from trainer import TrainerStructureFactory, TrainerSourceTypeEnum, TrainerClientServerMessage, TrainerClientServerMessageTypeEnum


if len(sys.argv) != 5:
	print(f"Failed to provide expected arguments: main.py [image size integer] [training_batch_size] [training_epochs] [label_classes_total]")
else:

	image_size = int(sys.argv[1])
	training_batch_size = int(sys.argv[2])
	training_epochs = int(sys.argv[3])
	label_classes_total = int(sys.argv[4])

	# create data yaml file
	with open("/app/yolov5/data/service_data.yaml", "w") as file_handle:
		file_handle.writelines([
			f"train: /app/training/\n",
			f"val: /app/validation/\n",
			f"\n",
			f"# number of classes\n",
			f"nc: {label_classes_total}\n",
			f"\n",
			f"# class names\n",
			f"names: [{','.join([f'class_{x}' for x in range(label_classes_total)])}]"
		])

	trainer_server_messenger = ServerMessenger(
		server_socket_factory_and_local_host_pointer_per_source_type={
			TrainerSourceTypeEnum.ImageSource: (
				ServerSocketFactory(
					is_debug=False
				),
				HostPointer(
					host_address="0.0.0.0",
					host_port=31982
				)
			)
		},
		client_server_message_class=TrainerClientServerMessage,
		source_type_enum_class=TrainerSourceTypeEnum,
		server_messenger_source_type=TrainerSourceTypeEnum.Trainer,
		structure_factory=TrainerStructureFactory(
			script_directory_path="/app/scripts",
			temp_image_directory_path="/app/temp_images",
			training_directory_path="/app/training",
			validation_directory_path="/app/validation",
			model_directory_path="/app/models",
			image_size=image_size,
			training_batch_size=training_batch_size,
			training_epochs=training_epochs,
			is_debug=True
		),
		is_debug=False
	)

	trainer_server_messenger.start_receiving_from_clients()

	try:
		is_running = True
		while is_running:
			time.sleep(1.0)
	finally:
		try:
			trainer_server_messenger.stop_receiving_from_clients()
		finally:
			trainer_server_messenger.dispose()
