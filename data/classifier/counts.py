import pandas as pd
from collections import Counter

df = pd.read_csv(f'all_train_clean_new.csv',sep=',')
Counter(df.label)