python /app/yolov5/train.py --img $1 --cfg yolov5n.yaml --batch $2 --epochs $3 --data service_data.yaml --weights "$4"
# TODO create "--data" file and copy into appropriate location while Docker image is building
# TODO ensure that "--weights" can actually find the appropriate file path