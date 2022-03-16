docker rm test_gpu_exists_gpu
docker run \
  --name test_gpu_exists_gpu \
  --gpus all \
  --ipc=host \
  --env NVIDIA_DISABLE_REQUIRE=1 \
  test_gpu_exists_gpu:latest
