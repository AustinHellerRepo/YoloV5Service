FROM nvcr.io/nvidia/pytorch:21.10-py3

RUN apt update && apt install -y zip htop screen libgl1-mesa-glx
RUN python -m pip install --upgrade pip

WORKDIR /app

RUN git clone https://github.com/ultralytics/yolov5

WORKDIR /app/yolov5

RUN pip install -r requirements.txt
RUN pip uninstall -y torch torchvision torchtext
RUN pip install --no-cache -r requirements.txt albumentations wandb gsutil notebook \
    torch==1.10.2+cu113 torchvision==0.11.3+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html

CMD