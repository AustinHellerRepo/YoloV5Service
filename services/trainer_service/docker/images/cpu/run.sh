rm -f /home/austin/Projects_Unversioned/YoloV5Service/trainer/training/labels.cache
rm -f /home/austin/Projects_Unversioned/YoloV5Service/trainer/training/labels.cache.npy
docker rm yolov5_trainer_cpu
docker run \
  --name yolov5_trainer_cpu \
  -p 31982:31982 \
  -e image_size=2048 \
  -e training_batch_size=1 \
  -e training_epochs=3 \
  -e label_classes_total=1 \
  -v $HOME/Projects_Unversioned/YoloV5Service/trainer/temp_images:/app/temp_images \
  -v $HOME/Projects_Unversioned/YoloV5Service/trainer/training:/app/training \
  -v $HOME/Projects_Unversioned/YoloV5Service/trainer/validation:/app/validation \
  -v $HOME/Projects_Unversioned/YoloV5Service/trainer/models:/app/models \
  yolov5_trainer_cpu:latest