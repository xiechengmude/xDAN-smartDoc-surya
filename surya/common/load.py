from typing import Optional, Any, Union

import torch

from surya.settings import settings


class ModelLoader:
    def __init__(self, checkpoint: Optional[str] = None):
        self.checkpoint = checkpoint

    def model(
        self,
        device: Union[torch.device, str, None] = settings.TORCH_DEVICE_MODEL,
        dtype: Optional[Union[torch.dtype, str]] = settings.MODEL_DTYPE,
    ) -> Any:
        raise NotImplementedError()

    def processor(
        self,
        device: Union[torch.device, str, None] = settings.TORCH_DEVICE_MODEL,
        dtype: Optional[Union[torch.dtype, str]] = settings.MODEL_DTYPE,
    ) -> Any:
        raise NotImplementedError()
