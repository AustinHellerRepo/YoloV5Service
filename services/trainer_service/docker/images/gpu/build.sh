cd ../../../../..
docker build "$@" -t yolov5_trainer_gpu:latest --build-arg CACHEBUST=$(date +%Y-%m-%d:%H:%M:%S) -f services/trainer_service/docker/images/gpu/Dockerfile .