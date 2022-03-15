from __future__ import annotations
import unittest
from ..client import ClientStructure, ClientMessengerFactory, ClientSocketFactory, DetectorClientServerMessage
from austin_heller_repo.common import HostPointer


def get_default_client_structure() -> ClientStructure:
	return ClientStructure(
		detector_client_messenger_factory=ClientMessengerFactory(
			client_socket_factory=ClientSocketFactory(),
			server_host_pointer=HostPointer(
				host_address="0.0.0.0",
				host_port=31983
			),
			client_server_message_class=DetectorClientServerMessage,
			is_debug=False
		)
	)


class ClientTest(unittest.TestCase):

	def test_initialize(self):

		client_structure = get_default_client_structure()

		self.assertIsNotNone(client_structure)

		client_structure.dispose()

	def test_detect_labels(self):

		client_structure = get_default_client_structure()

		detected_labels = client_structure.get_detected_labels(
			image_file_path="/home/austin/Projects_Unversioned/YoloV5Service/trainer/training/images/1a88e1b1-5c28-47ad-ba3c-33b92db5e8b3.png"
		)

		print(f"Found {len(detected_labels)} labels.")

		client_structure.dispose()
