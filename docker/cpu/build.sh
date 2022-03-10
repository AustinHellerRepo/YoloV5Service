#docker build "$@" -t yolov5_service_cpu:latest .
cd ../..
docker build "$@" -t yolov5_service_cpu:latest -f docker/cpu/Dockerfile .