FROM anibali/pytorch:1.8.1-cuda11.1-ubuntu20.04
CMD python -c "import torch; device = torch.device('cuda' if torch.cuda.is_available() else 'cpu'); print('Using device:', device); torch.rand(10).to(device);"
