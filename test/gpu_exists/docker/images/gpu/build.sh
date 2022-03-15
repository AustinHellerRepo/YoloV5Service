cd ../../../../..
docker build "$@" -t test_gpu_exists_gpu:latest -f test/gpu_exists/docker/images/gpu/Dockerfile .