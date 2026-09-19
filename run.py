# for data loading
import pandas as pd
import os
import glob
import json

# for classification
import spacy

from pipeline.comparison import SimilarityClassifier

classifier = SimilarityClassifier()

inbox_dir = "data_v2/inbox"
mail_files = os.path.join(inbox_dir, "*.json") # all mail as json files
mail_files_list = sorted(glob.glob(mail_files)) # list of all json files

# for each mail file, read and add the mail information to dataframe
mail_data = []
for mail_file in mail_files_list:
    with open(mail_file, "r") as mfile:
        mail_data.append(pd.json_normalize(json.loads(mfile.read())))

# Convert the extracted JSON fields to a dataframe.
mail_df = pd.concat(mail_data, ignore_index=True)

# Classify every email in the inbox.
classification_results = mail_df.apply(
    lambda row: classifier.classify(row.to_dict()),
    axis=1,
)

mail_df["predicted_label"] = classification_results.apply(
    lambda result: result["label"]
)
mail_df["confidence"] = classification_results.apply(
    lambda result: result["confidence"]
)

print(f"Classified {len(mail_df)} emails")
print(mail_df[["email_id", "predicted_label", "confidence"]].to_string(index=False))