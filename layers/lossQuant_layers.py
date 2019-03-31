import torch 
from torch._jit_internal import weak_module, weak_script_method, List
from torch.nn.modules.utils import _pair
import torch.nn.functional as F
from torch.nn.parameter import Parameter
from math import sqrt
from device import device
from layers.common import QLayer
from functions import loss_quant_connect

class LinearQuantLin(torch.nn.Module, QLayer):
    def __init__(self, in_features, out_features, bias=True, bottom=-1, top=1, size=5, alpha=1):
        torch.nn.Module.__init__(self)
        self.in_features = in_features
        self.out_features = out_features
        self.bottom = bottom
        self.top = top
        self.register_buffer("alpha", torch.Tensor([alpha]).to(device))
        self.weight = torch.nn.Parameter(torch.Tensor(out_features, in_features))
        if bias:
            self.bias = torch.nn.Parameter(torch.Tensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()
        self.linear_op = loss_quant_connect.QuantLinDense(size=size, bottom=bottom, top=top)

    def reset_parameters(self):
        self.weight.data.uniform_(self.bottom, self.top)
        if self.bias is not None:
            self.bias.data.zero_()

    def clamp(self):
        self.weight.data.clamp_(self.bottom, self.top)
        if not self.bias is None:
            self.bias.data.clamp_(self.bottom, self.top) 

    def set_alpha(self, alpha):
        self.alpha = torch.Tensor([alpha]).to(device)


    def forward(self, input):
        return self.linear_op.apply(input, self.weight, self.bias, self.alpha)


class LinearQuantLog(torch.nn.Module, QLayer):
    def __init__(self, in_features, out_features, bias=True, gamma=2, init=0.25, size=5, alpha=1):
        super(LinearQuantLog, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.gamma = gamma
        self.init = init
        self.size = size
        self.register_buffer("alpha", torch.Tensor([alpha]).to(device))
        self.weight = torch.nn.Parameter(torch.Tensor(out_features, in_features))
        if bias:
            self.bias = torch.nn.Parameter(torch.Tensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()
        self.linear_op = loss_quant_connect.QuantLogDense(gamma=gamma, init=init, size=size)

    def reset_parameters(self):
        self.weight.data.uniform_(-self.init*self.gamma**(self.size-1), self.init*self.gamma**(self.size-1))
        if self.bias is not None:
            self.bias.data.zero_()

    def clamp(self):
        self.weight.data.clamp_(-self.init*self.gamma**(self.size-1), self.init*self.gamma**(self.size-1))
        if not self.bias is None:
            self.bias.data.clamp_(-self.init*self.gamma**(self.size-1), self.init*self.gamma**(self.size-1))

    def set_alpha(self, alpha):
        self.alpha = torch.Tensor([alpha]).to(device)


    def forward(self, input):
        return self.linear_op.apply(input, self.weight, self.bias, self.alpha)


class QuandConv2d(torch.nn.Conv2d, QLayer):
    def __init__(self, *args,  bottom=-1, top=1, size=5, alpha=1,  stride=1, padding=1, dilation=1, groups=1):
        torch.nn.Conv2d.__init__(self, *args,  stride=stride, padding=padding, dilation=dilation, groups=groups)
        self.top = top
        self.bottom = bottom
        self.size = size
        self.register_buffer("alpha", torch.Tensor([alpha]).to(device))
        self.conv_op = loss_quant_connect.QuantConv2d(size=self.size, bottom=self.bottom, top=self.top, stride=stride, padding=padding, dilation=dilation, groups=groups)


    def reset_parameters(self):
        self.weight.data.uniform_(self.bottom, self.top)
        if self.bias is not None:
            self.bias.data.zero_()

    def clamp(self):
        self.weight.data.clamp_(self.bottom, self.top)
        if not self.bias is None:
            self.bias.data.clamp_(self.bottom, self.top) 

    def set_alpha(self, alpha):
        self.alpha = torch.Tensor([alpha]).to(device)

    def forward(self, input):
        out = self.conv_op.apply(input, self.weight, self.bias, self.alpha)
        return out