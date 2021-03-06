## this file corresponds to the random exploration policy
## please refer to the detailed comments in exploration_policy_linucb.py file because the functions are very similar, the only difference is the exploration policy function, here we use the random exploration policy 

import click
from pathlib import Path
from sklearn.utils import shuffle

import pickle as pkl
import gzip
import pandas as pd
import tensorflow as tf
import numpy as np
import random
import os
from sklearn.preprocessing import StandardScaler
import models 
import utils
import math

def update(concat, y_concat, pipeline_id, dataset_idx, reward):
    
    ## this corresponds to the update of (i) R(t-1) to R'(t) 
    ## input 
    ## y_concat - training data, is called concat because at each round we concatenate the new knowledge to the previous knowledge
    ## concat - training meta-features, un-used in the paper
    ## reward : observed performance for pipeline_idx on dataset_idx
    ## nb_steps = correspond to s parameter in the paper
    ## step_size corresponds to s parameter in the paper


    if math.isnan(y_concat.loc[dataset_idx,pipeline_id])  :
        concat = utils.append_update(concat, dataset_idx, pipeline_id, reward)
        y_concat.loc[dataset_idx, pipeline_id] = reward

    return concat, y_concat


def regret_rdm(X_init, y_init, knowledge, output_dir, fold_id):
    
    ## please refer to the comments in function regret_ucb in exploration_policy_linucb.py file because the functions are very similar, the only difference is the exploration policy function, here we use the random exploration policy described in the paper
    
    reward = []

    epochs = 75
    latent_size = 40
    
    nb_steps = 0
    buffer = 0
    
    explored = []
    
    recommended2 = []
    recommended3 = []
    
    optimal = []
    
    for dataset_idx in y_init.index:
        
        y_substr = pd.DataFrame( y_init.loc[dataset_idx] ).T
        X_substr = pd.DataFrame( X_init.loc[dataset_idx] ).T
        
        _, _, y, choix = utils.create_random(None, None, y_substr, knowledge) # we use the random exploration policy
        explored.append(choix)
        
        if dataset_idx == 0:

            
            concat2 = utils.formating(y, X_substr)
            y_concat2 = y.copy()
            
            concat3 = utils.formating(y, X_substr)
            y_concat3 = y.copy()
            
            
        else:
            
            y_concat2 = pd.concat([y_concat2, y])
            concat2 = utils.append(concat2, y, X_substr) # from R(t-1) to R'(t)
            
            y_concat3 = pd.concat([y_concat3, y])
            concat3 = utils.append(concat3, y, X_substr) # from R(t-1) to R'(t)

            
        test = utils.pred_formating(y, X_substr)
        

        
        ### MF+bias
        history2, prediction2, timer2, _ = models.one_fold(output_dir,concat2, test, y_concat2, y, '2', epochs, latent_size, knowledge, fold_id)
        reward_mf_bias, top, rcd_pipeline_id, top_pipeline_id = utils.update_argmax(y_substr, prediction2) # from R'(t) to R(t)
        recommended2.append(rcd_pipeline_id)
        concat2, y_concat2 = update(concat2, y_concat2, rcd_pipeline_id, dataset_idx, reward_mf_bias)
        tf.keras.backend.clear_session()

        ### NeurCF
        history3, prediction3, timer3, _ = models.one_fold(output_dir,concat3, test, y_concat3, y, '3', epochs, latent_size, knowledge, fold_id)
        reward_neurcf, top, rcd_pipeline_id, top_pipeline_id = utils.update_argmax(y_substr, prediction3) # from R(t-1) to R'(t)
        recommended3.append(rcd_pipeline_id)
        concat3, y_concat3 = update(concat3, y_concat3, rcd_pipeline_id, dataset_idx, reward_neurcf)
        tf.keras.backend.clear_session()
        
        #### Random from C(t)
        y_rdm = y.copy()
        y_rdm[np.isnan(y_rdm)] = 0
        reward_rdm, top, rcd_pipeline_id, top_pipeline_id = utils.update_argmax(y_substr, y_rdm)
        
        
        # store and save info 
        reward.append( [reward_mf, reward_mf_bias, reward_neurcf, reward_rdm, top] ) #reward_knn
        full_recommendation = [ recommended1, recommended2, recommended3] 
        optimal.append(top_pipeline_id)
        
        with gzip.open( os.path.join(output_dir, 'RDM_reward_{}_{}.pkl.gz'.format(fold_id, knowledge) )  ,'wb') as f:
            pkl.dump(reward,f)
            pkl.dump(explored,f)
            pkl.dump(full_recommendation,f)
            pkl.dump(optimal,f)
        
    return True



@click.command()
@click.option('--input-dir', default=None, help='Project input directory.')
@click.option('--output-dir', default=None, help='Experiment output directory.')
def main(input_dir, output_dir):

    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        print("Output folder created: {}".format(output_dir))
        
    #######################################
    ############# PARAMETERS TO EXPLORE
    #######################################
    
    for fold_id in range(10):
        
        X_init, y_init = utils.load_data_175_avg('a', 666)

        X_init, y_init = shuffle(X_init, y_init)

        y_init = y_init.reset_index(drop=True)
        X_init = X_init.reset_index(drop=True)
    
        print('2')
        regret_rdm(X_init,y_init, 2, output_dir, fold_id)
        print('4')
        regret_rdm(X_init,y_init,  4, output_dir, fold_id)
        print('6')
        regret_rdm(X_init,y_init, 6, output_dir, fold_id)

        
if __name__ == "__main__":
    main()

