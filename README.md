# Trilogues
This repository contains the basic scripts used for scaling the trilogue tabes collected by the "EUINACTION" project. 



### Dependencies
**GPU REQUIRED**
Install CUDA from https://developer.nvidia.com/cuda-downloads

Install the following python modules using pip or conda:

- Python >= 3.6 
- Pandas
- nltk
- traceback
- huggingface transformers
- huggingface datasets
- statistics

## Instructions

### Training

1. Provide `base_path` in the training.py. Subsequently, change the name of the training and test data in the `train_data`, `test_data` variable. Lastly, provide the name of the model in the `trainer.save_model()` function call.
2. Run the command `CUDA_VISIBLE_DEVICES=<GPU-ID> python training.py`.

### Scaling
1. For scaling, we need to run scaling_inference.py. Provide `data_base_path` folder where the trilogue csvs are, `model_base_path` folder where the model files are, and `write_base_path` folder for the output.
2. Run the command `CUDA_VISIBLE_DEVICES=<GPU-ID> python scaling_inference.py`.
3. The output of the scaling will be in one folder in the write_base_path named `final_output_scaling.csv`.

For any queries, kindly open an issue. 

