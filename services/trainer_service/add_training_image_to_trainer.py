from __future__ import annotations
import sys
import time
from austin_heller_repo.common import HostPointer

try:
	from .image_source import ImageSourceStructure, ClientMessengerFactory, ClientSocketFactory, TrainerClientServerMessage
except ImportError:
	from image_source import ImageSourceStructure, ClientMessengerFactory, ClientSocketFactory, TrainerClientServerMessage


if len(sys.argv) != 5:
	print(f"Missing at least one commandline argument.")
else:

	trainer_host_address = sys.argv[1]
	trainer_host_port = int(sys.argv[2])
	image_file_path = sys.argv[3]
	annotation_file_path = sys.argv[4]

	image_source_structure = ImageSourceStructure(
		trainer_client_messenger_factory=ClientMessengerFactory(
			client_socket_factory=ClientSocketFactory(),
			server_host_pointer=HostPointer(
				host_address=trainer_host_address,
				host_port=trainer_host_port
			),
			client_server_message_class=TrainerClientServerMessage,
			is_debug=False
		)
	)

	time.sleep(1.0)

	image_source_structure.send_training_image(
		image_file_path=image_file_path,
		annotation_file_path=annotation_file_path
	)

	image_source_structure.dispose()
