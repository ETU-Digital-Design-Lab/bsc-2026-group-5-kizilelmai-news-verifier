import pandas as pd
df1 = pd.read_csv('data/gold_500/claims_annotated.csv')
df2 = pd.read_csv('data/raw/isakulaksiz_dataset.csv')
for t in df1['text'].head(10):
  print(any(t[:20] in str(x) for x in df2['description'].fillna('')))
