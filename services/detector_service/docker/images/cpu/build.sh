cd ../../../../..
docker build "$@" -t yolov5_detector_cpu:latest --build-arg CACHEBUST=$(date +%Y-%m-%d:%H:%M:%S) -f services/detector_service/docker/images/cpu/Dockerfile .