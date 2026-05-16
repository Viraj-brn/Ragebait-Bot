import pandas as pd
import os

def prepare_sarcasm_data():
    # Define file paths relative to the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, 'data', 'train-balanced-sarcasm.csv')
    output_file = os.path.join(base_dir, 'data', 'cleaned_sarcasm.csv')

    print("Loading raw dataset...")
    try:
        # Load the dataset (it's big, so we'll just read the columns we need)
        df = pd.read_csv(input_file, usecols=['label', 'comment', 'parent_comment'])
    except FileNotFoundError:
        print(f"[ERROR] Could not find {input_file}. Make sure you downloaded it from Kaggle!")
        return

    # Filter 1: Keep ONLY the sarcastic comments (label == 1)
    df = df[df['label'] == 1].copy()

    # Filter 2: Drop any rows where the comment is missing
    df = df.dropna(subset=['comment'])

    # Filter 3: We want punchy one-liners. 
    # Keep comments that are between 20 and 150 characters.
    df['comment_length'] = df['comment'].apply(lambda x: len(str(x)))
    df = df[(df['comment_length'] >= 20) & (df['comment_length'] <= 150)]

    # Filter 4: Randomly sample 15,000 rows. 
    # This is plenty for our Vector DB and keeps processing lightning fast.
    if len(df) > 15000:
        df = df.sample(n=15000, random_state=42)

    # Save the cleaned, lean dataset
    df[['parent_comment', 'comment']].to_csv(output_file, index=False)
    
    print(f"[OK] Data cleaned successfully!")
    print(f"[OK] Saved {len(df)} punchy, sarcastic comments to {output_file}")

if __name__ == "__main__":
    prepare_sarcasm_data()