import torch 
from torch._jit_internal import weak_module, weak_script_method, List
from torch.nn.modules.utils import _pair
import torch.nn.functional as F
from torch.nn.parameter import Parameter
from math import sqrt

from functions import binary_connect

class LinearBin(torch.nn.Module):
    def __init__(self, in_features, out_features, bias=True):
        super(LinearBin, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = torch.nn.Parameter(torch.Tensor(out_features, in_features))
        if bias:
            self.bias = torch.nn.Parameter(torch.Tensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()

    def reset_parameters(self):
        self.weight.data.normal_(0, 1 * (sqrt(1. / self.in_features)))
        if self.bias is not None:
            self.bias.data.zero_()

    def clamp(self):
        self.weight.data.clamp_(-1, 1)
        if not self.bias is None:
            self.bias.data.clamp_(-1, 1) 

    def forward(self, input):
        if self.bias is not None:
            return binary_connect.BinaryDense.apply(input, self.weight, self.bias)
        return binary_connect.BinaryDense.apply(input, self.weight)


class BinarizeConv2d(torch.nn.Conv2d):

    def __init__(self, *kargs, **kwargs):
        super(BinarizeConv2d, self).__init__(*kargs, **kwargs)
        self.conv_op = binary_connect.BinaryConv2d(self.stride,
                                   self.padding, self.dilation, self.groups)
    def clamp(self):
        self.weight.data.clamp_(-1, 1)
        #if not self.bias is None:
        #    self.bias.data.clamp_(-1, 1)


    def forward(self, input):
        out = self.conv_op.apply(input, self.weight, self.bias)
        return out


class ShiftNormBatch1d(torch.nn.Module):
    __constants__ = ['momentum', 'eps']
    def __init__(self, in_dim, eps=1e-5, momentum=0.1):
        super(ShiftNormBatch1d, self).__init__()
        self.in_features = in_dim
        self.weight = torch.nn.Parameter(torch.Tensor(self.in_features))
        self.bias = torch.nn.Parameter(torch.Tensor(self.in_features))

        self.register_buffer('running_mean', torch.zeros(self.in_features))
        self.register_buffer('running_var', torch.ones(self.in_features))

        self.eps = eps
        self.momentum = momentum


    def forward(self, x):
        self.running_mean =  (1 - self.momentum) * self.running_mean + self.momentum * torch.mean(x,0).detach()
        self.running_var  =  (1 - self.momentum) * self.running_var  + self.momentum * torch.mean((x-self.running_mean)*binary_connect.AP2(x-self.running_mean),0).detach()

        return binary_connect.ShiftBatch.apply(x, self.running_mean, self.running_var, self.weight, self.bias, self.eps)




class ShiftNormBatch2d(torch.nn.Module):
    __constants__ = ['momentum', 'eps']
    def __init__(self, in_channels, eps=1e-5, momentum=0.1):
        super(ShiftNormBatch2d, self).__init__()
        self.in_features = in_channels
        self.weight = torch.nn.Parameter(torch.Tensor(self.in_features))
        self.bias = torch.nn.Parameter(torch.Tensor(self.in_features))

        self.register_buffer('running_mean', torch.zeros(self.in_features))
        self.register_buffer('running_var', torch.ones(self.in_features))

        self.eps = eps
        self.momentum = momentum

    @staticmethod
    def _tile(tensor, dim):
        return tensor.repeat(dim[0],dim[1],1).transpose(2,0)

    def forward(self, x):
        dim = x.size()[-2:]

        self.running_mean =  (1 - self.momentum) * self.running_mean + self.momentum * torch.mean(x,[0,2,3]).detach()
        curr_mean = ShiftNormBatch2d._tile(self.running_mean, dim)

        self.running_var  =  (1 - self.momentum) * self.running_var  + self.momentum * torch.mean((x-curr_mean)*binary_connect.AP2(x-curr_mean),[0,2,3]).detach()

        return binary_connect.ShiftBatch.apply(x, curr_mean, ShiftNormBatch2d._tile(self.running_var, dim), ShiftNormBatch2d._tile(self.weight, dim), ShiftNormBatch2d._tile(self.bias, dim), self.eps)