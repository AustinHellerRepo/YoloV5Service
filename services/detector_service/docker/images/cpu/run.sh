docker rm yolov5_detector_cpu
docker run \
  --name yolov5_detector_cpu \
  --network host \
  -e image_size=2048 \
  -e label_classes_total=2 \
  -v $HOME/Projects_Unversioned/YoloV5Service/detector/temp_images:/app/temp_images \
  -v $HOME/Projects_Unversioned/YoloV5Service/detector/models:/app/models \
  yolov5_detector_cpu:latest