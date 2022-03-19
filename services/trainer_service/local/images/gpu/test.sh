cd temp
if [ -d "./venv/bin" ]
then
	source ./venv/bin/activate
else
	source ./venv/Scripts/activate
fi
python ./main.py 2048 1 1 2 "./training" "./validation" "./models" "./temp_images" "./scripts" "./yolov5" "0.0.0.0" 37642 37644
