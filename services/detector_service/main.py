from __future__ import annotations
import os
import sys
import time
from austin_heller_repo.socket_queued_message_framework import ServerMessenger, ServerSocketFactory, HostPointer, ClientMessengerFactory, ClientSocketFactory

try:
	from .detector import DetectorStructureFactory, DetectorSourceTypeEnum, DetectorClientServerMessage, TrainerClientServerMessage
except ImportError:
	from detector import DetectorStructureFactory, DetectorSourceTypeEnum, DetectorClientServerMessage, TrainerClientServerMessage


if len(sys.argv) != 3:
	print(f"Failed to provide expected arguments: main.py")
else:

	image_size = int(sys.argv[1])
	label_classes_total = int(sys.argv[2])

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

	detector_server_messenger = ServerMessenger(
		server_socket_factory_and_local_host_pointer_per_source_type={
			DetectorSourceTypeEnum.Client: (
				ServerSocketFactory(
					is_debug=False
				),
				HostPointer(
					host_address="0.0.0.0",
					host_port=31983
				)
			)
		},
		client_server_message_class=DetectorClientServerMessage,
		source_type_enum_class=DetectorSourceTypeEnum,
		server_messenger_source_type=DetectorSourceTypeEnum.Trainer,
		structure_factory=DetectorStructureFactory(
			script_directory_path="/app/scripts",
			temp_image_directory_path="/app/temp_images",
			model_directory_path="/app/models",
			trainer_client_messenger_factory=ClientMessengerFactory(
				client_socket_factory=ClientSocketFactory(),
				server_host_pointer=HostPointer(
					host_address="0.0.0.0",
					host_port=31984
				),
				client_server_message_class=TrainerClientServerMessage,
				is_debug=False
			),
			image_size=image_size,
			is_debug=True
		),
		is_debug=False
	)

	detector_server_messenger.start_receiving_from_clients()

	try:
		is_running = True
		while is_running:
			time.sleep(1.0)
	finally:
		try:
			detector_server_messenger.stop_receiving_from_clients()
		finally:
			detector_server_messenger.dispose()
