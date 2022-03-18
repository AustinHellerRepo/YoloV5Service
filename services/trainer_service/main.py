from __future__ import annotations
import os
import sys
import time
from datetime import datetime
from austin_heller_repo.socket_queued_message_framework import ServerMessenger, ServerSocketFactory, HostPointer

try:
	from .trainer import TrainerStructureFactory, TrainerSourceTypeEnum, TrainerClientServerMessage, TrainerClientServerMessageTypeEnum
except ImportError:
	from trainer import TrainerStructureFactory, TrainerSourceTypeEnum, TrainerClientServerMessage, TrainerClientServerMessageTypeEnum


if len(sys.argv) != 14:
	print(f"{datetime.utcnow()}: script: Failed to provide expected arguments: main.py [image size integer] [training_batch_size] [training_epochs] [label_classes_total] [training directory path] [validation directory path] [models directory path] [temp images directory path] [scripts directory path] [yolov5 directory path] [host address] [image source port] [detector port]")
else:

	image_size = int(sys.argv[1])
	training_batch_size = int(sys.argv[2])
	training_epochs = int(sys.argv[3])
	label_classes_total = int(sys.argv[4])
	training_directory_path = sys.argv[5]
	validation_directory_path = sys.argv[6]
	models_directory_path = sys.argv[7]
	temp_images_directory_path = sys.argv[8]
	scripts_directory_path = sys.argv[9]
	yolov5_directory_path = sys.argv[10]
	host_address = sys.argv[11]
	image_source_port = int(sys.argv[12])
	detector_port = int(sys.argv[13])

	if training_directory_path[-1] == "/":
		training_directory_path = training_directory_path[:-1]
	if validation_directory_path[-1] == "/":
		validation_directory_path = validation_directory_path[:-1]
	if models_directory_path[-1] == "/":
		models_directory_path = models_directory_path[:-1]
	if temp_images_directory_path[-1] == "/":
		temp_images_directory_path = temp_images_directory_path[:-1]
	if scripts_directory_path[-1] == "/":
		scripts_directory_path = scripts_directory_path[:-1]
	if yolov5_directory_path[-1] == "/":
		yolov5_directory_path = yolov5_directory_path[:-1]

	service_data_file_path = os.path.join(yolov5_directory_path, "data", "service_data.yaml")

	# create data yaml file
	absolute_training_directory_path = os.path.abspath(training_directory_path)
	absolute_validation_directory_path = os.path.abspath(validation_directory_path)
	with open(service_data_file_path, "w") as file_handle:
		file_handle.writelines([
			f"train: {absolute_training_directory_path}/\n",
			f"val: {absolute_validation_directory_path}/\n",
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
					host_address=host_address,
					host_port=image_source_port
				)
			),
			TrainerSourceTypeEnum.Detector: (
				ServerSocketFactory(
					is_debug=False
				),
				HostPointer(
					host_address=host_address,
					host_port=detector_port
				)
			)
		},
		client_server_message_class=TrainerClientServerMessage,
		source_type_enum_class=TrainerSourceTypeEnum,
		server_messenger_source_type=TrainerSourceTypeEnum.Trainer,
		structure_factory=TrainerStructureFactory(
			script_directory_path=scripts_directory_path,
			temp_image_directory_path=temp_images_directory_path,
			training_directory_path=training_directory_path,
			validation_directory_path=validation_directory_path,
			model_directory_path=models_directory_path,
			yolov5_directory_path=yolov5_directory_path,
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
