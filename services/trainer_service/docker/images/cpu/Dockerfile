FROM nvcr.io/nvidia/pytorch:21.10-py3

RUN apt update && apt install -y zip htop screen libgl1-mesa-glx
RUN python -m pip install --upgrade pip

WORKDIR /app

RUN git clone https://github.com/ultralytics/yolov5

WORKDIR /app/yolov5

#RUN pip install -r requirements.txt
#RUN pip uninstall -y torch torchvision torchtext
RUN pip install \
    #--no-cache \
    -r requirements.txt albumentations wandb gsutil notebook \
    git+https://github.com/AustinHellerRepo/SocketQueuedMessageFramework \
    torch==1.10.2+cpu torchvision==0.11.3+cpu torchaudio==0.10.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html

ARG CACHEBUST=1
RUN echo "$CACHEBUST"

RUN mkdir -p /app/scripts
RUN mkdir -p /app/temp_images/training
RUN mkdir -p /app/temp_images/validation
RUN mkdir -p /app/training/images
RUN mkdir -p /app/training/labels
RUN mkdir -p /app/validation/images
RUN mkdir -p /app/validation/labels
RUN mkdir -p /app/models

WORKDIR /app

COPY ./services/trainer_service/main.py ./main.py
COPY ./services/trainer_service/trainer.py ./trainer.py

WORKDIR /app/scripts

COPY ./services/trainer_service/docker/scripts/train.sh ./train.sh

CMD ["sh", "-c", "python /app/main.py ${image_size} ${training_batch_size} ${training_epochs} ${label_classes_total}"]