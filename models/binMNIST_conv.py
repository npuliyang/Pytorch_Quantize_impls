import torch 
import torch.nn as nn
from layers.binary_layers import LinearBin, BinarizeConv2d
from functions import binary_connect

class BinMNIST(torch.nn.Module):
    def __init__(self, in_features, out_features, num_units=2048):

        super(BinMNIST, self).__init__()
        
        self.conv1 = BinarizeConv2d(1, 32, kernel_size=3, padding=1)
        self.norm1   = nn.BatchNorm2d(32, eps=1e-4, momentum=0.15)

        self.conv2 = BinarizeConv2d(32, 64, kernel_size=3, padding=1)
        self.pool2   =  nn.MaxPool2d(kernel_size=3, stride=2)
        self.norm2   = nn.BatchNorm2d(64, eps=1e-4, momentum=0.15)

        self.linear3 = LinearBin(10816, num_units)#64 * 13 *  13
        self.norm3   = nn.BatchNorm1d(num_units, eps=1e-4, momentum=0.15)

        self.linear4 = LinearBin(num_units, out_features)
        self.norm4   = nn.BatchNorm1d(out_features, eps=1e-4, momentum=0.15)
        
        self.activation     = nn.ReLU()
        self.act_end = nn.LogSoftmax()

    def reset(self):
        #self.linear1.reset_parameters()
        #self.linear2.reset_parameters()    
        self.linear3.reset_parameters()
        self.linear4.reset_parameters()


    def clamp(self):
        #self.linear1.clamp()
        #self.linear2.clamp()
        self.linear3.clamp()
        self.linear4.clamp()


    def forward(self, x, dropout=True):


        x = self.activation(self.conv1(x.view(-1, 1, 28, 28)))
        x = self.norm1(x)
        #x = binary_connect.BinaryConnectDeterministic.apply(x)
        
        x = self.activation(self.conv2(x))
        x = self.pool2(x)
        x = self.norm2(x)
        x = binary_connect.BinaryConnectDeterministic.apply(x)

        x = x.view(x.size(0), -1)
        x = self.activation(self.linear3(x))
        x = self.norm3(x)
        x = binary_connect.BinaryConnectDeterministic.apply(x)


        x = self.linear4(x)
        return x
