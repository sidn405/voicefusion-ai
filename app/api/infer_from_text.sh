#!/bin/bash

TEXT="$2"
OUTPUT="$4"

cd "$(dirname "$0")"

echo "$TEXT" > tmp_input.txt

python3 -m espnet2.bin.tts_inference \
  --ngpu 0 \
  --data_path_and_name_and_type tmp_input.txt,text,text \
  --train_config exp/your_model/config.yaml \
  --model_file exp/your_model/train.loss.best.pth \
  --output_dir exp/api_output \
  --vocoder_file none \
  --vocoder_config "" \
  --fs 22050

mv exp/api_output/*.wav "$OUTPUT"
rm tmp_input.txt
