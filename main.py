from __future__ import annotations
import os
import sys
import time
from service import ServiceStructure


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
			f"train: /app/training/images/\n",
			f"val: /app/validation/images/\n",
			f"\n",
			f"# number of classes\n",
			f"nc: {label_classes_total}\n",
			f"\n",
			f"# class names\n",
			f"names: [{','.join([f'class_{x}' for x in range(label_classes_total)])}]"
		])

	service_structure = ServiceStructure(
		script_directory_path="/app/scripts",
		temp_image_directory_path="/app/temp_images",
		training_directory_path="/app/training",
		validation_directory_path="/app/validation",
		model_directory_path="/app/models",
		image_size=image_size,
		training_batch_size=training_batch_size,
		training_epochs=training_epochs
	)

	is_running = True
	while is_running:
		time.sleep(1.0)

	service_structure.dispose()
