import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import random

class ResidualLinear(nn.Module):

    def __init__(self, input_channel,dropout_rate=0.0):
        super(ResidualLinear,self).__init__()
        self.layer=nn.Linear(input_channel,input_channel,bias=False)
        self.act=nn.GELU()
        self.batchnorm=nn.LayerNorm([input_channel])#nn.BatchNorm1d(input_channel)
        self.dropout=nn.Dropout(dropout_rate)
    def forward(self,x):
        tmpx=x
        x=self.batchnorm(x)  
        x=self.layer(x)
        #x=self.batchnorm(x)  
        x=self.act(x)             
        x=self.dropout(x)
        x=x+tmpx
        return x

class Model(nn.Module):
    """
    CNN using Separable Convolution 2D with ResNet structure
    - Uses separable convolutions for efficiency
    - Applies ResNet residual connections when input_channels == output_channels
    - Suitable for image classification tasks
    """
    
    def __init__(self,input_features=9, num_classes=2, dropout_rate=0.0,verbose=False,scale=64,layer_num=5,mean_trend=None,std_trend=None,mean_feature=None,std_feature=None):
        super(Model, self).__init__()
        
        self.input_features = input_features
        self.num_classes = num_classes
        
        self.scale=scale

        self.layer_num=layer_num

        

        self.linear_head=nn.ModuleList()

        self.linear_head.append(nn.Sequential(

                nn.Linear( input_features,  self.scale*8,bias=False),
                #nn.BatchNorm1d(self.scale*8),     
                nn.GELU(),                
                #nn.LayerNorm([self.scale*16]),            
                nn.Dropout(dropout_rate)
        ))
        for i in range(layer_num):
            self.linear_head.append(ResidualLinear(self.scale*8,dropout_rate=dropout_rate))

        
        # Classifier head
        self.dropout = nn.Dropout(dropout_rate)
        
        self.fc2 = nn.Sequential(
            #ResidualLinear(self.scale*8,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*8,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*16,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*16,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*16,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*16,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*16,dropout_rate=dropout_rate),
            #ResidualLinear(self.scale*16,dropout_rate=dropout_rate),
            #nn.Dropout(dropout_rate),

            #nn.Linear( self.scale*16, self.scale*16),
            #nn.GELU(),
            #nn.BatchNorm1d(self.scale*16), 

            #nn.Dropout(dropout_rate),

            #nn.Linear( self.scale*8, num_classes),
            nn.BatchNorm1d(self.scale*8),  
            nn.Linear( self.scale*8, num_classes,bias=False),

        )


        if not isinstance(mean_feature, torch.Tensor):
            mean_feature = torch.tensor(mean_feature).float()
        if not isinstance(std_feature, torch.Tensor):
            std_feature = torch.tensor(std_feature).float()
        eps=torch.tensor(1e-6).float()

        self.register_buffer('mean_feature', mean_feature)
        self.register_buffer('std_feature', std_feature)
        self.register_buffer('eps', eps)


    def get_default_noise_config(self):
        """Provides a safe and comprehensive default configuration for augmentations."""
        return {
            # --- Augmentations for the Raw Signal (x) ---
            'low_freq_sine': {
                'p': 0.7,           # Probability of applying this noise
                'freq_range': (1, 5), # How many full cycles in the signal length
                'amplitude_ratio': 0.05 # Amplitude as a ratio of signal's std dev
            },
            'high_freq_gaussian': {
                'p': 0.7,
                'noise_level': 0.05  # Standard deviation of the noise
            },
            'cutout': {
                'p': 0.7,
                'cutout_ratio': 0.1  # Fraction of the signal length to zero out
            },
            'speckle': {
                'p': 0.7,
                'noise_level': 0.015
            },
            # --- Augmentations for Features (x_feature & x_embedding) ---
            'feature_gaussian': {
                'p': 1.0,
                'noise_level': 0.05
            },
            'feature_dropout': {
                'p': 1.0,
                'dropout_p': 0.5    # Probability of an element being zeroed
            }
        }


    def add_comprehensive_noise(
        self,        
        x_feature,
        config=None
    ):
        """
        Applies a probabilistic suite of augmentations to input tensors.

        Each possible augmentation has an independent probability of being applied,
        allowing for a rich combination of noisy samples. This includes signal-specific
        noise like low-frequency sine waves and high-frequency noise.

        Args:
            x (torch.Tensor): The raw signal tensor of shape (N, C, L).
            x_feature (torch.Tensor): Engineering features tensor of shape (N, K).
            x_embedding (torch.Tensor): Embedding tensor of shape (N, M).
            config (dict, optional): A dictionary to override default augmentation
                parameters. Use `get_default_noise_config()` to see the structure.

        Returns:
            tuple[torch.Tensor, torch.Tensor, torch.Tensor]: The augmented tensors.
        """
        # --- 1. Setup Configuration ---
        cfg = self.get_default_noise_config()
        if config is not None:
            # A simple way to merge user config into defaults
            for key, value in config.items():
                if key in cfg:
                    cfg[key].update(value)

        # --- 2. Clone Tensors to Avoid Modifying Originals ---
        
        aug_x_feature = x_feature.clone()
        

        device = aug_x_feature.device

        # ===================================================================
        

        # ===================================================================
        # Section B: Augmentations for Feature & Embedding Tensors
        # ===================================================================

        # --- Gaussian Noise for Features & Embeddings ---
        if random.random() < cfg['feature_gaussian']['p']:
            level = cfg['feature_gaussian']['noise_level']
            aug_x_feature += torch.randn_like(aug_x_feature) * level
            

        # --- Dropout for Features & Embeddings ---
        if random.random() < cfg['feature_dropout']['p']:
            p = cfg['feature_dropout']['dropout_p']
            aug_x_feature *= (torch.rand_like(aug_x_feature) > p).float()
            

        return aug_x_feature

    
    def forward(self,x_feature,start_index=0,train=False):
        #print(self.mean,self.std)        
        
        mean_feature=self.mean_feature
        
        std_feature=self.std_feature
        x_feature=(x_feature-mean_feature)/(std_feature+self.eps)
        x_feature=torch.nan_to_num(x_feature, nan=0.0)
        #print(x.shape)
        #x=torch.permute(x,(0,2,1))
        #print(x.shape)
        if train :
            #print(x_feature)
            x_feature=self.add_comprehensive_noise(x_feature)
            #print(x_feature)
        
        for layer in self.linear_head:
            x_feature=layer(x_feature)
             
        
        x=x_feature
        #x=x
        #x=x_feature
        #x=x_feature#+x_embedding
        #x=torch.cat((x_feature,x_embedding),dim=1)
        #x=x
        #x=x_feature+x_embedding
        #x=self.dropout(x)
        x=self.fc2(x)
        #print(x.shape)
        return x

def read_file_to_list(filepath):
  """
  Reads a text file and returns a list of strings, with each string being a row.
  """
  with open(filepath, 'r') as file:
    lines = []
    for line in file:
      lines.append(line.strip())
  return lines





class PotingModel:

    def __init__(self,device='cuda'):
        model_path = './ecg/msai-model/2026-02-02_18-39-09_flatten/best_balanced_accuracy_macro_score_0.6977911152831667.pth'
        state_dict = torch.load(model_path, map_location=device)
        input_features = state_dict['linear_head.0.0.weight'].shape[1]
        mean_feature = state_dict['mean_feature']
        std_feature = state_dict['std_feature']
        self.num_classes = state_dict['fc2.1.weight'].shape[0]
        self.new_columns= read_file_to_list('./ecg/msai-model/columns_0223.txt')

        self.model=Model(input_features=input_features,mean_feature=mean_feature,std_feature=std_feature,num_classes=self.num_classes,scale=16,layer_num=1024)
        if state_dict is not None:
            self.model.load_state_dict(state_dict)
        self.model.to(device)
        self.model.eval()
        self.device=device

    def predict(self,feature_dict):
        #print(feature_dict)
        x_feature=np.zeros(len(self.new_columns))
        for i,col in enumerate(self.new_columns):
            if col in feature_dict:
                x_feature[i]=feature_dict[col]
            else:
                x_feature[i]=np.nan
        
        with torch.no_grad():
            x_feature=torch.tensor(x_feature).float().to(self.device)
            x_feature=x_feature.unsqueeze(0)  # Add batch dimension
            output=self.model(x_feature,start_index=0,train=False)
            print(output)
            probs=F.sigmoid(output)
            print(probs)
            return probs.cpu().numpy()
        


if __name__ == "__main__":
    model=PotingModel()