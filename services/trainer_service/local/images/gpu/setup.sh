rm -rf temp
mkdir temp
cd temp
git clone https://github.com/ultralytics/yolov5
mkdir -p training/images
mkdir -p training/labels
mkdir -p validation/images
mkdir -p validation/labels
mkdir -p temp_images/training
mkdir -p temp_images/validation
mkdir models
mkdir scripts
python -m venv venv
source ./venv/bin/activate
pip install -r ./yolov5/requirements.txt
pip install \
    albumentations wandb gsutil notebook \
    git+https://github.com/AustinHellerRepo/SocketQueuedMessageFramework \
    torch==1.10.2+cu113 torchvision==0.11.3+cu113 torchaudio==0.10.2+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
cp ../../../../main.py ./main.py
cp ../../../../trainer.py ./trainer.py
cp ../../../../scripts/train.sh ./scripts/train.sh
