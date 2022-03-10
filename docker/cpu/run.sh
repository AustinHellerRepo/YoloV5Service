docker rm yolov5_service_cpu
docker run --name yolov5_service_cpu -e image_size=2048 -e training_batch_size=1 -e training_epochs=3 -e label_classes_total=1 yolov5_service_cpu:latest