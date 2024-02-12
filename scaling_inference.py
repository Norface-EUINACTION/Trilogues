# -*- coding: utf-8 -*-
"""scaling-trilogs-roberta.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19-n8SclgV9SfPh1TWJLZsl6m1ZAg0Kbo
"""
import datetime
import os
import time
import sys
import re
import numpy as np
import random
import pandas as pd
import nltk
import numpy as np
import json
import glob
import torch
from torch.utils.data import Dataset, DataLoader, random_split, RandomSampler, SequentialSampler
torch.manual_seed(50)

from datasets.dataset_dict import DatasetDict
from datasets import load_metric, load_dataset, Dataset 
from transformers import RobertaTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import statistics

from collections import Counter

nltk.download('punkt')

#from google.colab import drive
#drive.mount('/content/drive', force_remount=True)
token_list = ["$deleted$", "$Paragraph 5 is deleted$", 
      "$Article 13 is deleted$", "$<bi>[no change]</bi>$", 
      "$[no change]$", "$no changes proposed by the Commission$",
      "$No corresponding proposal by the Commission$", "$deleted$",
      "$<bi>deleted</bi>$", "$Not amended$", "$<bi>[no change]</bi>$",
      "$<bi>[no chang</bi><bi>e]</bi>$" , "$No Change$", "$[No change]$", 
      "$no change$", "$DELETED$", "<b>$Not amended$</b>" ,
      "$[moved to Art. 1 a below]$", "$Idem$", "$No changes to COM proposal$", 
      "$no changes to the Commission's text$", "$no change to Commission text$", 
      "<i>$Unchanged$</i>", "$Unchanged$" , "$Deleted and replaced by$", "$As COM$", 
      "$AS COM$",  "$deleted (Amendment 3)$", "$Not acceptable. There is no corresponding article in the text.", 
      "$Not acceptable", "$Acceptable with modifications$", "$Not Acceptable", "$Keep the text from COM proposal$", 
      "$Need to be further discussed.$", "$Need to be further discussed.$", 
      "$Keep Council text (i.e. deletion )", "$Keep the text from COM proposal$",
      "$Not acceptable Keep the text from COM proposal", "$Acceptable$", "$reject$", 
      "$accept$", "$Amendment acceptable$", "$Not acceptable.$", "$<b>Acceptable</b>$", 
      "$<b>Not acceptable</b>$", "$Commission text retained$", "$Commission Text retained$", 
      "$(deleted)$", "$Accept EP amendment$", "$Not $Accept EP amendment$$",
      "$Merged with recital 21$", "$Deleted (merged with Article 8)$",
      "$Deleted (merged with Article 7)$",
      "$[transferred in modified form to recitals 11a-11d]$", 
      "$Point 7 has been deleted$"]

deleted = [token for token in token_list if "deleted" in token.lower()]
no_change = [token for token in token_list if "change" in token.lower()]
agree = [token for token in token_list if "com" in token.lower()]


data_base_path = '/ceph/sobaidul/data/Full_sample_parsed_trilogues'
write_base_path = '/ceph/sobaidul/data/scaled_trilogs_5'
model_base_path = '/work/sobaidul/trilog_classifier/trilog_training_data_all_clean/Roberta-large-upscaling-pos-new'
#!unzip /content/drive/MyDrive/trilog_training_data/upscaling-roberta.zip -d /content/drive/MyDrive/trilog_training_data

tokenizer = RobertaTokenizer.from_pretrained("roberta-large")
model = AutoModelForSequenceClassification.from_pretrained(model_base_path, num_labels=3)

def preprocess_function(batch):
    return tokenizer(batch["text"], truncation=True, padding="max_length")

def pre_process(coms, eps, council):
  regex = r'\W+'
  html = re.compile(r'<[^>]+>')
  c = list()
  e = list()
  d = list()
  for i, j, k  in zip(coms, eps, council):
     i = re.sub("\s\s+" , " ", i)
     i = re.sub(html, " ", i)
     i = re.sub(regex, " ", i)
     j = re.sub(html , " ", j)
     j = re.sub(regex, " ", j)
     k = re.sub(html, " ", k)
     k = re.sub(regex, " ", k)
     c.append(i)
     e.append(j)
     d.append(k)
     
  return c, e, d

def get_tokenized_data(position):
  df_dataset = pd.DataFrame(position, columns=['text'])
  dataset = Dataset.from_pandas(pd.DataFrame(data=df_dataset))
  dataset = DatasetDict({
      'test': dataset})
  dataset
  tokenized_data = dataset.map(preprocess_function, batched=True)

  return tokenized_data

def run_prediction(trainer,tokenized_data):
  predictions = trainer.predict(test_dataset=tokenized_data["test"])
  preds = predictions.predictions.argmax(-1)
  #print(predictions[0])
  score = (np.exp(predictions[0])/np.exp(predictions[0]).sum(-1,keepdims=True)).max(1)
  scores = (np.exp(predictions[0])/np.exp(predictions[0]).sum(-1,keepdims=True))
  #print(scores)
  return preds, score, scores

def get_scores_for_labels(scores):
  scores_0 = list()
  scores_1 = list()
  scores_2 = list()
  for i in scores:
    scores_0.append(i[0])
    scores_1.append(i[1])
    scores_2.append(i[2])


  return scores_0, scores_1, scores_2

def filename(f):
  l = f.split('/')
  return l[-1]

def contains(test_string, test_list):
  flag=0
  if any(word in test_string.lower() for word in test_list):
    #print(True)
    flag = 1
  return flag 

#driver code
file_list = glob.glob(f'{data_base_path}/*.csv')

trainer = Trainer(model=model)
logf = open(f"{write_base_path}/error.log", "w")
for i in file_list:
  trilog_name = filename(i)
  try:
    df = pd.read_csv(i, sep=',')
    trilog_name = filename(i)
    df1 = df.copy()
    df1 = df1.fillna('')
    COMS = list(df1.COM)
    EP = list(df1.EP)
    Council = list(df1.Council)
    COMS, EP, Council = pre_process(COMS,EP,Council)
    position_list = [COMS,EP,Council]

    for idx, i in enumerate(position_list):
      test_dataset = get_tokenized_data(i)
      predictions, probs, all_probs = run_prediction(trainer, test_dataset)
      probs_0, probs_1, probs_2 = get_scores_for_labels(all_probs)
      if idx == 0:
        df['prediction_COM'] = predictions
        df['prob_COM'] = probs
        df['prob_COM_0'] = probs_0
        df['prob_COM_1'] = probs_1
        df['prob_COM_2'] = probs_2

      elif idx == 1:
        df['prediction_EP'] = predictions
        df['prob_EP'] = probs
        df['prob_EP_0'] = probs_0
        df['prob_EP_1'] = probs_1
        df['prob_EP_2'] = probs_2  

      elif idx == 2:
        df['prediction_Council'] = predictions
        df['prob_Council'] = probs 
        df['prob_Council_0'] = probs_0
        df['prob_Council_1'] = probs_1
        df['prob_Council_2'] = probs_2  

    df.to_csv(f'{write_base_path}/scaled_{trilog_name}', sep=',', index=False)
  except Exception as e:
    print("Exception: " + str(e))
    print("For file: " + str(trilog_name))
    logf.write("Failed to open and run {0}: {1}\n".format(str(i), str(e)))
    try:
      df = pd.read_csv(i, sep=',', encoding='unicode_escape')
      trilog_name = filename(i)
      df1 = df.copy()
      df1 = df1.fillna('')
      COMS = list(df1.COM)
      EP = list(df1.EP)
      Council = list(df1.Council)
      COMS, EP, Council = pre_process(COMS,EP,Council)
      position_list = [COMS,EP,Council]

      for idx, i in enumerate(position_list):
        test_dataset = get_tokenized_data(i)
        predictions, probs, all_probs = run_prediction(trainer, test_dataset)
        probs_0, probs_1, probs_2 = get_scores_for_labels(all_probs)
        if idx == 0:
          df['prediction_COM'] = predictions
          df['prob_COM'] = probs
          df['prob_COM_0'] = probs_0
          df['prob_COM_1'] = probs_1
          df['prob_COM_2'] = probs_2

        elif idx == 1:
          df['prediction_EP'] = predictions
          df['prob_EP'] = probs
          df['prob_EP_0'] = probs_0
          df['prob_EP_1'] = probs_1
          df['prob_EP_2'] = probs_2  

        elif idx == 2:
          df['prediction_Council'] = predictions
          df['prob_Council'] = probs 
          df['prob_Council_0'] = probs_0
          df['prob_Council_1'] = probs_1
          df['prob_Council_2'] = probs_2  

      df.to_csv(f'{write_base_path}/scaled_{trilog_name}.csv', sep=',', index=False)
    except Exception as e:
      print("Exception: " + str(e))
      print("For file: " + str(trilog_name))
      logf.write("Cannot open and run with encoding parameter {0}: {1}\n".format(str(i), str(e)))

logf.close()

'''
####################################################
#combine all files

file_name = glob.glob(f'{write_base_path}/*.csv')

df_list = list()
for i in file_name:
  temp_df = pd.read_csv(i, sep=',')
  df_list.append(temp_df)

df_all = pd.concat(df_list, ignore_index=True)

#####################################################
#adjust positions w.r.t COM


df_all = df_all[df_all['prediction_COM'].notna()]
df_all = df_all[df_all['prediction_Council'].notna()]
df_all = df_all[df_all['prediction_EP'].notna()]
df_all[['prediction_COM', 'prediction_EP', 'prediction_Council']] = df_all[['prediction_COM', 'prediction_EP', 'prediction_Council']].applymap(np.int64)
df_all
df_copy = df_all.copy()
df_copy = df_copy.fillna('')
df_copy.fillna({'EP':'empty', 'Council':'empty'}, inplace=True)
COMS = list(df_copy.COM)
EP = list(df_copy.EP)
Council = list(df_copy.Council)


pred_com = list(df_copy.prediction_COM)
pred_ep = list(df_copy.prediction_EP)
pred_council = list(df_copy.prediction_Council)

prob_COM = list(df_copy.prob_COM)
prob_EP = list(df_copy.prob_EP)
prob_Council = list(df_copy.prob_Council)

prob_COM_0 = list(df_copy.prob_COM_0)
prob_COM_1 = list(df_copy.prob_COM_1)
prob_COM_2 = list(df_copy.prob_COM_2)

prob_EP_0 = list(df_copy.prob_EP_0)
prob_EP_1 = list(df_copy.prob_EP_1)
prob_EP_2 = list(df_copy.prob_EP_2)

prob_Council_0 = list(df_copy.prob_Council_0)
prob_Council_1 = list(df_copy.prob_Council_1)
prob_Council_2 = list(df_copy.prob_Council_2)

position_list = list(zip(COMS, EP, Council))

for idx , (com, ep, council) in enumerate(position_list):
  #if EP and Council are empty: reflect label of COM
  if ep == 'empty':
    pred_ep[idx] = pred_com[idx]
    prob_EP[idx] = prob_COM[idx]
    
    prob_EP_0[idx] = prob_COM_0[idx]
    prob_EP_1[idx] = prob_COM_1[idx]
    prob_EP_2[idx] = prob_COM_2[idx]



  if council == 'empty':
    pred_council[idx] = pred_com[idx]
    prob_Council[idx] = prob_COM[idx]

    prob_Council_0[idx] = prob_COM_0[idx]
    prob_Council_1[idx] = prob_COM_1[idx]
    prob_Council_2[idx] = prob_COM_2[idx]

  #if either EP or Council are deleted: then opposite of COM label
  check_ep_del = contains(ep, deleted)
  check_council_del = contains(council, deleted)

  if check_ep_del == 1:
    if pred_com[idx] == 1:
      pred_ep[idx] = 0

      prob_EP[idx] = prob_COM[idx]

      prob_EP_0[idx] = prob_COM_0[idx]
      prob_EP_1[idx] = prob_COM_1[idx]
      prob_EP_2[idx] = prob_COM_2[idx]      

    elif pred_com[idx] == 0:
      pred_ep[idx] = 1

      prob_EP[idx] = prob_COM[idx]

      prob_EP_0[idx] = prob_COM_0[idx]
      prob_EP_1[idx] = prob_COM_1[idx]
      prob_EP_2[idx] = prob_COM_2[idx]  

  if check_council_del == 1:
    if pred_com[idx] == 1:
      pred_council[idx] = 0

      prob_Council[idx] = prob_COM[idx]

      prob_Council_0[idx] = prob_COM_0[idx]
      prob_Council_1[idx] = prob_COM_1[idx]
      prob_Council_2[idx] = prob_COM_2[idx]
    elif pred_com[idx] == 0:
      pred_council[idx] = 1

      prob_Council[idx] = prob_COM[idx]

      prob_Council_0[idx] = prob_COM_0[idx]
      prob_Council_1[idx] = prob_COM_1[idx]
      prob_Council_2[idx] = prob_COM_2[idx]
  
  #if either EP or Council are nochange or agree: then same as COM label
  check_ep_no_change = contains(ep, no_change)
  check_council_no_change = contains(council, no_change)
  check_ep_agree = contains(ep, agree)
  check_council_agree = contains(council, agree)

  if check_ep_no_change == 1 or check_ep_agree == 1:
    pred_ep[idx] = pred_com[idx]
    prob_EP[idx] = prob_COM[idx]

    prob_EP_0[idx] = prob_COM_0[idx]
    prob_EP_1[idx] = prob_COM_1[idx]
    prob_EP_2[idx] = prob_COM_2[idx]  

  if check_council_no_change == 1 or check_council_agree == 1:
    pred_council[idx] = pred_com[idx]

    prob_Council[idx] = prob_COM[idx]

    prob_Council_0[idx] = prob_COM_0[idx]
    prob_Council_1[idx] = prob_COM_1[idx]
    prob_Council_2[idx] = prob_COM_2[idx]

df_all['prediction_EP'] = pred_ep
df_all['prediction_Council'] = pred_council

df_all['prob_EP'] = prob_EP
df_all['prob_Council'] = prob_Council


df_all['prob_EP_0'] = prob_EP_0
df_all['prob_EP_1'] = prob_EP_1
df_all['prob_EP_2'] = prob_EP_2

df_all['prob_Council_0'] = prob_EP_0
df_all['prob_Council_1'] = prob_EP_1
df_all['prob_Council_2'] = prob_EP_2

df_all.to_csv(f'{write_base_path}/scaled_trilogs_all_21-04-2023-evening.csv', sep=',', index=False )
'''