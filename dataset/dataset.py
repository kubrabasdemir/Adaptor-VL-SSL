from mgca.datasets.pretrain_dataset import (
    MultimodalPretrainingDataset, 
    multimodal_collate_fn, 
    BASE_DIR, 
)
from mgca.constants import *

from transformers import BertTokenizer
from transformers.tokenization_utils import PreTrainedTokenizerBase
from datasets import Dataset, concatenate_datasets

import torch 
import os
from pathlib import Path
import pickle

from tqdm import tqdm


class MultimodalPretrainingDatasetForAdaptor(MultimodalPretrainingDataset):
    def __init__(self, split="train", transform=None, data_pct=1.0,
                 imsize=256, max_words=128, sent_num=3, tokenizer=None):
        super().__init__(split=split, transform=transform, data_pct=data_pct, 
                         imsize=imsize, max_words=max_words, sent_num=sent_num)
        if isinstance(tokenizer, str):
            self.tokenizer = BertTokenizer.from_pretrained(tokenizer)
        elif isinstance(tokenizer, PreTrainedTokenizerBase):
            self.tokenizer = tokenizer
    
    def load_text_data(self, split):
        # get study to captions mapping
        # TODO: check this
        filepath = os.path.join(BASE_DIR, "../../data/captions.pickle")
        if not os.path.isfile(filepath):
            print(f"Caption file {filepath} does not exit. Creating captions...")
            path2sent = self.create_path_2_sent_mapping()
            with open(filepath, "wb") as f:
                pickle.dump(path2sent, f, protocol=2)
                print("Save to: ", filepath)
        else:
            with open(filepath, "rb") as f:
                path2sent = pickle.load(f)
    
        # filter studies to use for current split
        filenames = []
        total = len(self.df)
        with tqdm(total=total) as pbar:
            for row in self.df.itertuples():
                cur_split = getattr(row, MIMIC_CXR_SPLIT_COL)
                path = getattr(row, MIMIC_CXR_PATH_COL)
                
                ### Addition: make sure path points to an existing file ==========
                if not Path(path).is_file():
                    continue
                ### End addition =================================================
                
                if cur_split == split and path in path2sent:
                    filenames.append(path)
                
                pbar.update(1)
        return filenames, path2sent

def multimodal_collator(*args, **kwargs):
    d = multimodal_collate_fn(*args, **kwargs)
    d['input_ids'] = d.pop('caption_ids')
    d['pixel_values'] = d.pop('imgs')
    d['return_loss'] = True
    return d


# class MultimodalPretrainedEmbeddingsDataset(torch.utils.data.Dataset):
#     def __init__(self, text_embeds_raw, image_embeds_raw):
#         assert len(text_embeds_raw) == len(image_embeds_raw), "text and image embeds must have the same length"
#         self.text_embeds_raw = text_embeds_raw
#         self.image_embeds_raw = image_embeds_raw
        
#     def __len__(self):
#         return len(self.text_embeds_raw)
    
#     def __getitem__(self, idx):
#         return {'text_embeds_raw':self.text_embeds_raw[idx], 
#                 'image_embeds_raw':self.image_embeds_raw[idx]}
        

# class MultimodalPretrainedEmbeddingsDatasetLoader(object):
#     def __init__(
#         self, 
#         text_embeds_raw_dir: str,
#         image_embeds_raw_dir: str,
#         split: str='train',
#         device='cpu',
#         num_of_batches=-1, 
#     ):
#         self.text_embeds_raw_dir = os.path.join(text_embeds_raw_dir, split)
#         self.image_embeds_raw_dir = os.path.join(image_embeds_raw_dir, split)
#         self.device = torch.device(device)
#         self.num_of_batches = num_of_batches
            
#     def load_data(self) -> Dataset:
#         dataset = None
#         text_embeds_raw = []
#         image_embeds_raw = []
#         text_tensor_names = sorted([f for f in os.listdir(self.text_embeds_raw_dir)],
#                                    key=lambda x: int(x.split('_')[1].split('.')[0]))
#         image_tensor_names = sorted([f for f in os.listdir(self.image_embeds_raw_dir)], 
#                                     key=lambda x: int(x.split('_')[1].split('.')[0]))
#         if self.num_of_batches > 0:
#             text_tensor_names = text_tensor_names[:self.num_of_batches]
#             image_tensor_names = image_tensor_names[:self.num_of_batches]
#         assert text_tensor_names == image_tensor_names, "text and image tensor names do not match"
        
#         total = len(text_tensor_names)
#         with tqdm(total=total) as pbar:
#             for i, (text_tensor, image_tensor) in enumerate(zip(text_tensor_names, image_tensor_names)):
#                 text_tensor = torch.load(os.path.join(self.text_embeds_raw_dir, text_tensor), map_location=self.device)
#                 image_tensor = torch.load(os.path.join(self.image_embeds_raw_dir, image_tensor),  map_location=self.device)
#                 if isinstance(image_tensor, dict):  ### For ResNetAE
#                     image_tensor = image_tensor['z']
#                 text_embeds_raw.append(text_tensor)
#                 image_embeds_raw.append(image_tensor)
#                 if (i + 1) % 200 == 0 or i == total - 1:
#                     text_embeds_raw = torch.vstack(text_embeds_raw)
#                     image_embeds_raw = torch.vstack(image_embeds_raw)
#                     data = {'text_embeds_raw': text_embeds_raw, 'image_embeds_raw': image_embeds_raw}
#                     ds = Dataset.from_dict(data)
#                     dataset = ds if dataset is None else concatenate_datasets([dataset, ds])
#                 pbar.update(1)
#         return dataset
    
    
class MultimodalPretrainedEmbeddingsDataset(torch.utils.data.Dataset):
    def __init__(
        self, 
        text_embeds_raw_dir: str,
        image_embeds_raw_dir: str,
        split: str='train',
        device='cpu',
        num_of_batches=-1, 
    ):
        self.text_embeds_raw_dir = os.path.join(text_embeds_raw_dir, split)
        self.image_embeds_raw_dir = os.path.join(image_embeds_raw_dir, split)
        self.device = torch.device(device)
        self.num_of_batches = num_of_batches
        
        self.text_tensor_names = sorted([f for f in os.listdir(self.text_embeds_raw_dir)],
                                        key=lambda x: int(x.split('_')[1].split('.')[0]))
        self.image_tensor_names = sorted([f for f in os.listdir(self.image_embeds_raw_dir)], 
                                         key=lambda x: int(x.split('_')[1].split('.')[0]))
        if self.num_of_batches > 0:
            self.text_tensor_names = self.text_tensor_names[:self.num_of_batches]
            self.image_tensor_names = self.image_tensor_names[:self.num_of_batches]
        else:
            self.num_of_batches = len(self.text_tensor_names)
        
        assert self.text_tensor_names == self.image_tensor_names, "text and image tensor names do not match"
        self.batch_size = torch.load(os.path.join(self.text_embeds_raw_dir, self.text_tensor_names[0]), 
                                     map_location='cpu')[0].shape[0]
        
    def __getitem__(self, idx):
        batch_idx = idx // self.batch_size
        batch_item_idx = idx % self.batch_size
        
        text_tensor = torch.load(os.path.join(self.text_embeds_raw_dir, self.text_tensor_names[batch_idx]), 
                                 map_location=self.device)[batch_item_idx]
        image_tensor = torch.load(os.path.join(self.image_embeds_raw_dir, self.image_tensor_names[batch_idx]), 
                                  map_location=self.device)
        if isinstance(image_tensor, dict):  ### For ResNetAE
            image_tensor = image_tensor['z']
        image_tensor = image_tensor[batch_item_idx]
        
        # print('Single sample loaded. ')
        return {'text_embeds_raw':text_tensor, 'image_embeds_raw':image_tensor}

    def __len__(self):
        return self.num_of_batches * self.batch_size
    
    
class MultimodalPretrainedEmbeddingsIterableDataset(torch.utils.data.IterableDataset):
    def __init__(
        self, 
        text_embeds_raw_dir: str,
        image_embeds_raw_dir: str,
        split: str='train',
        device='cpu',
        num_of_batches=-1, 
        shuffle=True,
    ):
        super().__init__()
        self.text_embeds_raw_dir = os.path.join(text_embeds_raw_dir, split)
        self.image_embeds_raw_dir = os.path.join(image_embeds_raw_dir, split)
        self.device = torch.device(device)
        self.num_of_batches = num_of_batches
        
        self.text_tensor_names = sorted([f for f in os.listdir(self.text_embeds_raw_dir)],
                                        key=lambda x: int(x.split('_')[1].split('.')[0]))
        self.image_tensor_names = sorted([f for f in os.listdir(self.image_embeds_raw_dir)], 
                                         key=lambda x: int(x.split('_')[1].split('.')[0]))
        assert len(self.text_tensor_names) > 0, f"No tensor files found in the directory {self.text_embeds_raw_dir}"
        assert len(self.image_tensor_names) > 0, f"No tensor files found in the directory {self.image_embeds_raw_dir}"
        
        if self.num_of_batches > 0 and self.num_of_batches < len(self.text_tensor_names):
            self.text_tensor_names = self.text_tensor_names[:self.num_of_batches]
            self.image_tensor_names = self.image_tensor_names[:self.num_of_batches]
        else:
            self.num_of_batches = len(self.text_tensor_names)
        
        if shuffle:
            self.shuffle_batches()
        
        assert self.text_tensor_names == self.image_tensor_names, "text and image tensor names do not match"
        self.batch_size = torch.load(os.path.join(self.text_embeds_raw_dir, self.text_tensor_names[0]), 
                                     map_location='cpu')[0].shape[0]
    
    def process_single_tensor_file(self, text_tensor, image_tensor):
        for tt, it in zip(text_tensor, image_tensor):
            yield {'text_embeds_raw':tt, 'image_embeds_raw':it}
    
    def shuffle_batches(self):
        shuffled_idx = torch.randperm(self.num_of_batches)
        self.text_tensor_names = [self.text_tensor_names[i] for i in shuffled_idx]
        self.image_tensor_names = [self.image_tensor_names[i] for i in shuffled_idx]
    
    def __iter__(self):
        for text_tensor_name, image_tensor_name in zip(self.text_tensor_names, self.image_tensor_names):
            text_tensor = torch.load(os.path.join(self.text_embeds_raw_dir, text_tensor_name), 
                                     map_location=self.device)
            image_tensor = torch.load(os.path.join(self.image_embeds_raw_dir, image_tensor_name), 
                                      map_location=self.device)
            if isinstance(image_tensor, dict):  ### For ResNetAE
                image_tensor = image_tensor['z']
            
            yield from self.process_single_tensor_file(text_tensor, image_tensor)
    
    def __len__(self):
        return self.num_of_batches * self.batch_size
