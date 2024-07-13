from logger import logger
from pickletools import optimize
import torch
import numpy as np
from tqdm import tqdm
from transformers import AdamW, get_linear_schedule_with_warmup
from model import MRCModel
from load_data import traindataloader

N_EPOCHES = 30
LR = 5e-5
WARMUP_PROPORTION = 0.1
MAX_GRAD_NORM = 1.0
# MODEL_PATH = './bert-base-chinese'
MODEL_PATH = 'google-bert/bert-base-chinese'
SAVED_DIR = './saved_model'

device = "cuda" if torch.cuda.is_available() else "cpu"


def run():
    model = MRCModel.from_pretrained(MODEL_PATH)
    model.to(device)

    no_decay = ['bias', 'LayerNorm.bias', 'LayerNorm.weight']
    optimizer_group_parameters = [
        {'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
         'weight_decay': 0.01},
        {'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)], 'weight_decay': 0.0}
    ]
    total_steps = len(traindataloader)*N_EPOCHES
    optimizer = AdamW(optimizer_group_parameters,lr=LR,eps=1e-8)
    scheduler = get_linear_schedule_with_warmup(optimizer,num_warmup_steps=int(WARMUP_PROPORTION * total_steps), num_training_steps=total_steps)

    loss_vals = []
    logger.info("*"*15+"Start Training"+"*"*15)
    for epoch in range(N_EPOCHES):
        model.train()
        epoch_loss = []
        num = 0
        pbar = tqdm(traindataloader)
        pbar.set_description("[Train Epoch {}]".format(epoch))
        for batch_idx, batch_data in enumerate(pbar):
            input_ids = batch_data["input_ids"].to(device)
            attention_mask = batch_data["attention_mask"].to(device)
            token_type_ids = batch_data["token_type_ids"].to(device)
            start_ids = batch_data["start_ids"].to(device)
            end_ids = batch_data["end_ids"].to(device)
            num += len(input_ids)
            model.zero_grad()
            loss = model(input_ids,attention_mask,token_type_ids,start_ids,end_ids)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
            if batch_idx % 200 == 0:
                logger.info("Epoch=%d,batch_idx=%d,loss=%.4f"%(epoch,batch_idx,loss.item()))
            epoch_loss.append(loss.item())
            optimizer.step()
            scheduler.step()
            if num >= 3000:
                break
        loss_vals.append(np.mean(epoch_loss))
    logger.info("*"*15+"End Training"+"*"*15)
    model.save_pretrained(SAVED_DIR)


if __name__ == "__main__":
    run()
